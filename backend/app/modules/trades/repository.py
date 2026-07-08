"""Trade repository — filtered list with pagination.

Extends ``SqlAlchemyRepository[Trade]``. No business logic — pure data access.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.models.asset import Asset
from app.models.trade import Trade
from app.modules.shared.base import SqlAlchemyRepository


class TradeRepository(SqlAlchemyRepository[Trade]):
    """Repository for the ``trades`` table with dynamic filtered listing."""

    def __init__(self, session):
        super().__init__(session, Trade)

    async def get_by_ticket(self, account_id: int, broker_ticket: str) -> Trade | None:
        """Find a trade by account and broker ticket (for import dedup)."""
        stmt = select(Trade).where(
            Trade.account_id == account_id,
            Trade.broker_ticket == broker_ticket,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_closed(
        self,
        *,
        account_id: int | None = None,
        asset_id: int | None = None,
        market_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> list[Trade]:
        """Return closed trades matching optional filters, sorted by exit_datetime ASC.

        Single query with eager loading of account and asset relationships.
        ``market_id`` filter requires a join to the ``Asset`` model.
        """
        query = (
            select(Trade)
            .options(joinedload(Trade.account), joinedload(Trade.asset))
            .where(Trade.status == "closed")
        )

        if account_id is not None:
            query = query.where(Trade.account_id == account_id)
        if asset_id is not None:
            query = query.where(Trade.asset_id == asset_id)
        if market_id is not None:
            query = query.join(Trade.asset).where(Asset.market_id == market_id)
        if date_from is not None:
            query = query.where(Trade.exit_datetime >= date_from)
        if date_to is not None:
            query = query.where(Trade.exit_datetime <= date_to)

        query = query.order_by(Trade.exit_datetime.asc())

        result = await self._session.execute(query)
        return list(result.scalars().unique().all())

    async def list(
        self,
        status: str | None = None,
        direction: str | None = None,
        account_id: int | None = None,
        asset_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Trade], int]:
        """Return paginated trades matching the given filters.

        Default: active trades ordered by ``entry_datetime DESC``.
        """
        where_clauses: list = [Trade.is_active == (1 if is_active else 0)]

        if status is not None:
            where_clauses.append(Trade.status == status)
        if direction is not None:
            where_clauses.append(Trade.direction == direction)
        if account_id is not None:
            where_clauses.append(Trade.account_id == account_id)
        if asset_id is not None:
            where_clauses.append(Trade.asset_id == asset_id)
        if date_from is not None:
            where_clauses.append(Trade.entry_datetime >= date_from)
        if date_to is not None:
            where_clauses.append(Trade.entry_datetime <= date_to)
        if search is not None:
            where_clauses.append(Trade.notes_override.ilike(f"%{search}%"))

        # Total count
        count_stmt = select(func.count()).select_from(Trade).where(*where_clauses)
        total = (await self._session.execute(count_stmt)).scalar()

        # Paginated query
        stmt = (
            select(Trade)
            .where(*where_clauses)
            .order_by(Trade.entry_datetime.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        items = list((await self._session.execute(stmt)).scalars().all())

        return items, total
