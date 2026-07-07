"""Asset repository — dynamic filtered list with pagination.

Extends ``SqlAlchemyRepository[Asset]``. No business logic — pure data access.
"""

from sqlalchemy import func, select

from app.models.asset import Asset
from app.modules.shared.base import SqlAlchemyRepository


class AssetRepository(SqlAlchemyRepository[Asset]):
    """Repository for the ``assets`` table with symbol+market lookup and filtered listing."""

    def __init__(self, session):
        super().__init__(session, Asset)

    async def get_by_symbol_market(self, symbol: str, market_id: int) -> Asset | None:
        """Return an asset by composite key ``(symbol, market_id)``, or ``None``."""
        stmt = select(Asset).where(
            Asset.symbol == symbol,
            Asset.market_id == market_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        symbol: str | None = None,
        market_id: int | None = None,
        search: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Asset], int]:
        """Return paginated assets matching the given filters.

        - When ``symbol`` is provided WITHOUT ``market_id``: return ALL assets
          with that symbol (global search — no market_id filter applied).
        - When BOTH ``symbol`` AND ``market_id`` provided: filter by both.
        - Default: active only.
        """
        where_clauses: list = [Asset.is_active == (1 if is_active else 0)]

        if symbol:
            where_clauses.append(Asset.symbol == symbol)
        if market_id:
            where_clauses.append(Asset.market_id == market_id)
        if search:
            where_clauses.append(Asset.name.ilike(f"%{search}%"))

        # Total count
        count_stmt = select(func.count()).select_from(Asset).where(*where_clauses)
        total = (await self._session.execute(count_stmt)).scalar()

        # Paginated query
        stmt = (
            select(Asset)
            .where(*where_clauses)
            .order_by(Asset.symbol, Asset.market_id)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        items = list((await self._session.execute(stmt)).scalars().all())

        return items, total
