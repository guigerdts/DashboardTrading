"""Trade repository — filtered list with pagination.

Extends ``SqlAlchemyRepository[Trade]``. No business logic — pure data access.
"""

from sqlalchemy import func, select

from app.models.trade import Trade
from app.modules.shared.base import SqlAlchemyRepository


class TradeRepository(SqlAlchemyRepository[Trade]):
    """Repository for the ``trades`` table with dynamic filtered listing."""

    def __init__(self, session):
        super().__init__(session, Trade)

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
