"""Trade repository — filtered list with pagination.

Extends ``SqlAlchemyRepository[Trade]``. No business logic — pure data access.
"""

from datetime import datetime

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import contains_eager, joinedload

from app.models.asset import Asset
from app.models.trade import Trade
from app.modules.shared.base import SqlAlchemyRepository

# ── Sort column map ──────────────────────────────────────────────────────
# Maps public sort_by aliases to SQLAlchemy expressions.
# sort_by=symbol requires a join to Asset (shared with search).
# sort_by=net_pnl uses a CASE expression for computed PnL.

SORT_COLUMN_MAP: dict[str, tuple] = {
    "entry_datetime": (Trade.entry_datetime, False),
    "exit_datetime": (Trade.exit_datetime, False),
    "net_pnl": (
        case(
            (Trade.direction == "long", (Trade.exit_price - Trade.entry_price) * Trade.quantity),
            else_=(Trade.entry_price - Trade.exit_price) * Trade.quantity,
        )
        - func.coalesce(Trade.commission, 0)
        - func.abs(func.coalesce(Trade.swap_fees, 0)),
        False,
    ),
    "symbol": (Asset.symbol, True),  # requires join to Asset
    "broker_ticket": (Trade.broker_ticket, False),
}

# Default sort: entry_datetime DESC
_DEFAULT_SORT_BY = "entry_datetime"
_DEFAULT_SORT_DIR = "desc"


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
        sort_by: str = _DEFAULT_SORT_BY,
        sort_dir: str = _DEFAULT_SORT_DIR,
    ) -> tuple[list[Trade], int]:
        """Return paginated trades matching the given filters.

        ``sort_by`` must be one of the whitelist keys in ``SORT_COLUMN_MAP``.
        ``sort_dir`` must be ``asc`` or ``desc``.
        An ``id DESC`` tiebreaker is always appended for stable pagination.

        Default: active trades ordered by ``entry_datetime DESC``.
        """
        where_clauses: list[str] = [Trade.is_active == (1 if is_active else 0)]

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
            # OR-match over notes_override, broker_ticket, and asset.symbol
            search_clauses = [
                Trade.notes_override.ilike(f"%{search}%"),
                Trade.broker_ticket.ilike(f"%{search}%"),
            ]
            # Asset.symbol search requires the join — applied below
            search_clauses.append(Asset.symbol.ilike(f"%{search}%"))
            where_clauses.append(or_(*search_clauses))

        # Total count — must join Asset when search references Asset.symbol
        count_from = select(func.count())
        if search is not None:
            count_from = count_from.select_from(Trade).outerjoin(
                Trade.asset
            )
        else:
            count_from = count_from.select_from(Trade)
        count_stmt = count_from.where(*where_clauses)
        total = (await self._session.execute(count_stmt)).scalar()

        # ── Sort ──────────────────────────────────────────────────────
        # Resolve sort column from whitelist map
        sort_entry = SORT_COLUMN_MAP.get(sort_by)
        if sort_entry is None:
            raise ValueError(
                f"Invalid sort_by '{sort_by}'. Must be one of: {', '.join(SORT_COLUMN_MAP)}"
            )

        sort_expr, needs_join = sort_entry

        # Determine if we need an explicit join to Asset for WHERE/SORT
        needs_asset_join = needs_join or (search is not None)

        # Build the query — choose options based on whether we join to Asset
        if needs_asset_join:
            # Use LEFT OUTER JOIN to avoid excluding trades without assets
            stmt = (
                select(Trade)
                .outerjoin(Trade.asset)
                .options(contains_eager(Trade.asset), joinedload(Trade.account))
                .where(*where_clauses)
            )
        else:
            stmt = (
                select(Trade)
                .options(joinedload(Trade.account), joinedload(Trade.asset))
                .where(*where_clauses)
            )

        # Apply sort direction
        sort_column = sort_expr.desc() if sort_dir == "desc" else sort_expr.asc()

        # Stable sort tiebreaker (REQ-SPEC-02): always append id DESC
        stmt = stmt.order_by(sort_column, Trade.id.desc())

        # Pagination
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        items = list((await self._session.execute(stmt)).scalars().unique().all())

        return items, total

    async def get_summary(
        self,
        status: str | None = None,
        direction: str | None = None,
        account_id: int | None = None,
        asset_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
    ) -> dict:
        """Return aggregated trade summary scoped to the given filters.

        Single aggregate query using SQL CASE expressions — no Python loops.
        Returns: dict with ``total_trades``, ``total_pnl``, ``win_count``,
        ``loss_count``, ``win_rate``, ``avg_win``, ``avg_loss``,
        ``total_win_pnl``, ``total_loss_pnl``.
        """
        where_clauses: list = [Trade.is_active == 1]

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
            search_clauses = [
                Trade.notes_override.ilike(f"%{search}%"),
                Trade.broker_ticket.ilike(f"%{search}%"),
                Asset.symbol.ilike(f"%{search}%"),
            ]
            where_clauses.append(or_(*search_clauses))

        # PnL expression defined once, referenced in multiple CASE expressions
        pnl_expr = (
            case(
                (
                    Trade.direction == "long",
                    (Trade.exit_price - Trade.entry_price) * Trade.quantity,
                ),
                else_=(Trade.entry_price - Trade.exit_price) * Trade.quantity,
            )
            - func.coalesce(Trade.commission, 0)
            - func.abs(func.coalesce(Trade.swap_fees, 0))
        )

        # Build the aggregate query — join to Asset when search is active
        stmt = select(
            func.count().label("total_trades"),
            func.sum(pnl_expr).label("total_pnl"),
            func.sum(case((pnl_expr > 0, 1), else_=0)).label("win_count"),
            func.sum(case((pnl_expr < 0, 1), else_=0)).label("loss_count"),
            func.avg(case((pnl_expr > 0, pnl_expr))).label("avg_win"),
            func.avg(case((pnl_expr < 0, pnl_expr))).label("avg_loss"),
            func.sum(case((pnl_expr > 0, pnl_expr), else_=0)).label("total_win_pnl"),
            func.sum(case((pnl_expr < 0, pnl_expr), else_=0)).label("total_loss_pnl"),
        )

        if search is not None:
            stmt = stmt.select_from(Trade).outerjoin(Asset, Trade.asset_id == Asset.id)
        else:
            stmt = stmt.select_from(Trade)

        stmt = stmt.where(*where_clauses)

        row = (await self._session.execute(stmt)).one()

        total_trades = row.total_trades or 0
        total_pnl = round(float(row.total_pnl or 0), 2)
        win_count = row.win_count or 0
        loss_count = row.loss_count or 0
        avg_win = round(float(row.avg_win or 0), 2)
        avg_loss = round(float(row.avg_loss or 0), 2)
        total_win_pnl = round(float(row.total_win_pnl or 0), 2)
        total_loss_pnl = round(float(row.total_loss_pnl or 0), 2)
        win_rate = round(win_count / total_trades, 4) if total_trades > 0 else 0.0
        profit_factor = round(total_win_pnl / total_loss_pnl, 2) if total_loss_pnl > 0 else None

        return {
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
        }
