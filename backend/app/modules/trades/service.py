"""Trade service — business rule enforcement for trade operations.

BR-07:  Stop loss must be on the correct side of entry price.
BR-08:  Take profit must be on the correct side of entry price.
BR-09:  Stop loss and take profit must be on opposite sides of entry price.
BR-10:  exit_price and exit_datetime must both be NULL or both set.
BR-12:  Trades past their ``editable_until`` window cannot be modified.
BR-29:  DELETE sets ``is_active=False``, does NOT change ``status``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.db.unit_of_work import UnitOfWork
from app.models.trade import Trade
from app.modules.trades.schemas import (
    ReviewUpdate,
    TradeClose,
    TradeCreate,
    TradeFilters,
    TradeUpdate,
)


def _safe_catalog_name(rel) -> str | None:
    """Return the name attribute of a related object, or None."""
    return rel.name if rel is not None else None


def _compute_editable_until(status: str, entry_datetime: datetime | None = None) -> str | None:
    """Compute ``editable_until`` per BR-12.

    Open trades: no edit window (returns ``None``).
    Closed trades: 30 days from ``entry_datetime`` (or now if not provided).
    """
    if status == "open":
        return None
    base = entry_datetime or datetime.now(UTC)
    return (base + timedelta(days=30)).isoformat()


class TradeService:
    """Service layer for trade operations — all BR enforcement lives here."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(self, dto: TradeCreate) -> Trade:
        """Create a new trade.

        Validates BR-07/08/09 (SL/TP correctness) and BR-10 (exit consistency)
        before persisting.
        """
        self._validate_sl_tp(
            direction=dto.direction,
            entry_price=dto.entry_price,
            stop_loss=dto.stop_loss,
            take_profit=dto.take_profit,
        )
        self._validate_exit_consistency(
            status=dto.status,
            exit_price=dto.exit_price,
            exit_datetime=dto.exit_datetime,
        )

        trade = Trade(
            account_id=dto.account_id,
            asset_id=dto.asset_id,
            direction=dto.direction,
            status=dto.status,
            entry_price=dto.entry_price,
            quantity=dto.quantity,
            entry_datetime=dto.entry_datetime.isoformat(),
            exit_price=dto.exit_price,
            exit_datetime=dto.exit_datetime.isoformat() if dto.exit_datetime else None,
            stop_loss=dto.stop_loss,
            take_profit=dto.take_profit,
            position_size=dto.position_size,
            commission=dto.commission or 0,
            swap_fees=dto.swap_fees or 0,
            risk_amount=dto.risk_amount,
            broker_id=dto.broker_id,
            market_session_id=dto.market_session_id,
            timeframe_id=dto.timeframe_id,
            notes_override=dto.notes_override,
            editable_until=_compute_editable_until(dto.status, dto.entry_datetime),
        )

        await self.uow.trades.add(trade)
        self.logger.info("Created trade id=%d status=%s", trade.id, trade.status)
        return trade

    async def get(self, id: int) -> Trade:
        """Retrieve a trade by ID.

        Raises ``NotFoundError`` (404) if the trade does not exist.
        """
        trade = await self.uow.trades.get(id)
        if trade is None:
            raise NotFoundError(f"Trade with id {id} not found")
        return trade

    async def list(self, filters: TradeFilters) -> tuple[list[Trade], int]:
        """List trades with filters and pagination.

        Delegates to ``TradeRepository.list()`` with schema fields.
        """
        return await self.uow.trades.list(
            status=filters.status,
            direction=filters.direction,
            account_id=filters.account_id,
            asset_id=filters.asset_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            search=filters.search,
            is_active=filters.is_active,
            page=filters.page,
            page_size=filters.page_size,
            sort_by=filters.sort_by or "entry_datetime",
            sort_dir=filters.sort_dir or "desc",
        )

    async def get_summary(self, filters: TradeFilters) -> dict:
        """Return aggregated trade summary for the journal.

        Thin delegation to ``TradeRepository.get_summary()`` with filter fields
        extracted from the ``TradeFilters`` DTO.
        """
        return await self.uow.trades.get_summary(
            status=filters.status,
            direction=filters.direction,
            account_id=filters.account_id,
            asset_id=filters.asset_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            search=filters.search,
        )

    async def update(self, id: int, dto: TradeUpdate) -> Trade:
        """Update an existing trade.

        Enforces BR-12 (editable window) and re-validates BR-07/08/09 if
        SL/TP/direction/entry_price changed.
        """
        trade = await self.get(id)
        self._validate_editable(trade)

        update_data = dto.model_dump(exclude_unset=True)

        # Convert datetime fields to ISO strings for the model
        for field in ("entry_datetime", "exit_datetime"):
            if field in update_data and isinstance(update_data[field], datetime):
                update_data[field] = update_data[field].isoformat()

        # Apply all changes
        for field, value in update_data.items():
            setattr(trade, field, value)

        # Re-validate SL/TP if relevant fields changed
        if any(f in update_data for f in ("stop_loss", "take_profit", "direction", "entry_price")):
            self._validate_sl_tp(
                direction=trade.direction,
                entry_price=trade.entry_price,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
            )

        # Validate strategy/setup references if changed
        if "strategy_id" in update_data and update_data["strategy_id"] is not None:
            from app.models.strategy import Strategy
            from app.modules.catalogs.repository import CatalogRepository
            from app.modules.catalogs.service import CatalogService

            strat_svc = CatalogService(CatalogRepository(self.uow._session, Strategy))
            await strat_svc.get(update_data["strategy_id"])
            await strat_svc.validate_active_ids([update_data["strategy_id"]])

        if "setup_id" in update_data and update_data["setup_id"] is not None:
            from app.models.strategy import Setup
            from app.modules.catalogs.repository import CatalogRepository
            from app.modules.catalogs.service import CatalogService

            setup_svc = CatalogService(CatalogRepository(self.uow._session, Setup))
            await setup_svc.get(update_data["setup_id"])
            await setup_svc.validate_active_ids([update_data["setup_id"]])

        trade.updated_at = datetime.now(UTC).isoformat()
        self.logger.info("Updated trade id=%d fields=%s", id, set(update_data.keys()))
        return trade

    async def close(self, id: int, dto: TradeClose) -> Trade:
        """Close an open trade.

        Sets exit fields, marks status as 'closed', and computes a 30-day
        ``editable_until`` window. Raises ``BusinessRuleError`` if already closed.
        """
        trade = await self.get(id)
        if trade.status == "closed":
            raise BusinessRuleError(f"Trade with id {id} is already closed")

        trade.exit_price = dto.exit_price
        trade.exit_datetime = dto.exit_datetime.isoformat()
        trade.status = "closed"
        trade.editable_until = _compute_editable_until("closed")
        trade.updated_at = datetime.now(UTC).isoformat()

        self.logger.info("Closed trade id=%d exit_price=%s", id, dto.exit_price)
        return trade

    async def soft_delete(self, id: int) -> None:
        """BR-29: Soft-delete a trade by setting ``is_active=0``.

        Does NOT change ``status``.
        """
        trade = await self.get(id)
        trade.is_active = 0
        trade.updated_at = datetime.now(UTC).isoformat()
        self.logger.info("Soft-deleted trade id=%d", id)

    async def get_detail(self, id: int) -> dict:
        """Return enriched trade detail for the detail page.

        Loads account/asset relationships, computes PnL, duration,
        return %, and embeds the review if one exists.
        """
        trade = await self.uow.trades.get_with_relations(id)
        if trade is None:
            raise NotFoundError(f"Trade with id {id} not found")

        net_pnl = None
        duration_hours = None
        return_pct = None

        if trade.status == "closed" and trade.exit_price is not None:
            raw_pnl = (
                (trade.exit_price - trade.entry_price) * trade.quantity
                if trade.direction == "long"
                else (trade.entry_price - trade.exit_price) * trade.quantity
            )
            net_pnl = round(raw_pnl - trade.commission - abs(trade.swap_fees), 2)

            if trade.entry_price > 0 and trade.quantity > 0:
                return_pct = round(net_pnl / (trade.entry_price * trade.quantity) * 100, 4)

        if trade.status == "closed" and trade.exit_datetime and trade.entry_datetime:
            try:
                from datetime import datetime as dt

                entry = dt.fromisoformat(trade.entry_datetime)
                exit_dt = dt.fromisoformat(trade.exit_datetime)
                delta = exit_dt - entry
                duration_hours = round(delta.total_seconds() / 3600, 2)
            except (ValueError, TypeError):
                pass

        # Build tags list (from selectinload eager join)
        tags_data = [{"id": t.id, "name": t.name} for t in getattr(trade, "tags", []) or []]

        # Build mistakes list with notes (from selectinload eager join)
        mistakes_data = [
            {
                "id": me.mistake_id,
                "name": me.mistake.name if hasattr(me, "mistake") and me.mistake else None,
                "note": me.notes,
            }
            for me in getattr(trade, "mistakes", []) or []
        ]

        review = await self.uow.trades.get_review(id)
        review_data = None
        if review is not None:
            review_data = {
                "id": review.id,
                "trade_id": review.trade_id,
                "content": review.content,
                "lesson_learned": review.lesson_learned,
                "created_at": review.created_at,
                "updated_at": review.updated_at,
            }

        return {
            "id": trade.id,
            "account_id": trade.account_id,
            "asset_id": trade.asset_id,
            "direction": trade.direction,
            "status": trade.status,
            "entry_price": trade.entry_price,
            "quantity": trade.quantity,
            "entry_datetime": trade.entry_datetime,
            "exit_price": trade.exit_price,
            "exit_datetime": trade.exit_datetime,
            "stop_loss": trade.stop_loss,
            "take_profit": trade.take_profit,
            "position_size": trade.position_size,
            "commission": trade.commission or 0,
            "swap_fees": trade.swap_fees or 0,
            "risk_amount": trade.risk_amount,
            "broker_id": trade.broker_id,
            "market_session_id": trade.market_session_id,
            "timeframe_id": trade.timeframe_id,
            "broker_ticket": trade.broker_ticket,
            "asset_symbol": trade.asset.symbol if trade.asset else None,
            "account_name": trade.account.name if trade.account else None,
            "strategy_id": trade.strategy_id,
            "strategy_name": _safe_catalog_name(getattr(trade, "strategy", None)),
            "setup_id": trade.setup_id,
            "setup_name": _safe_catalog_name(getattr(trade, "setup", None)),
            "tags": tags_data,
            "mistakes": mistakes_data,
            "editable_until": trade.editable_until,
            "notes_override": trade.notes_override,
            "is_active": bool(trade.is_active),
            "created_at": trade.created_at,
            "updated_at": trade.updated_at,
            "has_review": bool(getattr(trade, "has_review", False)),
            "duration_hours": duration_hours,
            "net_pnl": net_pnl,
            "return_pct": return_pct,
            "review": review_data,
        }

    # ------------------------------------------------------------------
    # Context classification (tags, mistakes, strategy/setup)
    # ------------------------------------------------------------------

    async def sync_tags(self, id: int, tag_ids: list[int]) -> Trade:
        """Replace all tag associations for a trade (full-replacement).

        Validates:
        - Trade exists (404)
        - Trade is editable (BR-12)
        - All tag IDs exist and are active (422 if archived)

        Uses replace semantics: old tags not in ``tag_ids`` are removed.
        An empty list clears all tags.
        """
        trade = await self.get(id)
        self._validate_editable(trade)

        # Validate all tag IDs exist and are active
        if tag_ids:
            from app.models.tag import Tag
            from app.modules.catalogs.repository import CatalogRepository
            from app.modules.catalogs.service import CatalogService

            cat_svc = CatalogService(CatalogRepository(self.uow._session, Tag))
            await cat_svc.validate_active_ids(tag_ids)

        await self.uow.trades.sync_tags(id, tag_ids)
        self.logger.info("Synced tags for trade id=%d tags=%s", id, tag_ids)
        return await self.get(id)

    async def sync_mistakes(self, id: int, mistakes: list[dict]) -> Trade:
        """Replace all mistake associations for a trade (full-replacement).

        Each entry in ``mistakes`` is a dict with ``id`` (int, required)
        and ``note`` (str, optional). Notes are stored in the pivot row.

        Validates:
        - Trade exists (404)
        - Trade is editable (BR-12)
        - All mistake IDs exist and are active (422 if archived)
        """
        trade = await self.get(id)
        self._validate_editable(trade)

        # Extract IDs for validation
        mistake_ids = [m["id"] for m in mistakes]

        # Validate all mistake IDs exist and are active
        if mistake_ids:
            from app.models.mistake import Mistake
            from app.modules.catalogs.repository import CatalogRepository
            from app.modules.catalogs.service import CatalogService

            cat_svc = CatalogService(CatalogRepository(self.uow._session, Mistake))
            await cat_svc.validate_active_ids(mistake_ids)

        await self.uow.trades.sync_mistakes(id, mistakes)
        self.logger.info("Synced mistakes for trade id=%s", id)
        return await self.get(id)

    async def update_context(
        self, id: int, strategy_id: int | None = None, setup_id: int | None = None
    ) -> Trade:
        """Update a trade's strategy and/or setup references.

        Validates:
        - Trade exists (404)
        - Trade is editable (BR-12)
        - Referenced entities exist (404) and are active (422 if archived)

        Only fields that are not None are updated.
        """
        trade = await self.get(id)
        self._validate_editable(trade)

        from app.models.strategy import Setup, Strategy
        from app.modules.catalogs.repository import CatalogRepository
        from app.modules.catalogs.service import CatalogService

        if strategy_id is not None:
            strat_svc = CatalogService(CatalogRepository(self.uow._session, Strategy))
            await strat_svc.get(strategy_id)  # 404 if not found
            await strat_svc.validate_active_ids([strategy_id])
            trade.strategy_id = strategy_id

        if setup_id is not None:
            setup_svc = CatalogService(CatalogRepository(self.uow._session, Setup))
            await setup_svc.get(setup_id)  # 404 if not found
            await setup_svc.validate_active_ids([setup_id])
            trade.setup_id = setup_id

        trade.updated_at = datetime.now(UTC).isoformat()
        self.logger.info("Updated context trade id=%d", id)
        return trade

    async def get_review(self, id: int) -> dict | None:
        """Return the review for a trade, or a dict with null fields."""
        trade = await self.uow.trades.get(id)
        if trade is None:
            raise NotFoundError(f"Trade with id {id} not found")
        review = await self.uow.trades.get_review(id)
        if review is None:
            return None
        return {
            "id": review.id,
            "trade_id": review.trade_id,
            "content": review.content,
            "lesson_learned": review.lesson_learned,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
        }

    async def upsert_review(self, id: int, dto: ReviewUpdate) -> dict:
        """Upsert a trade review. Returns the serialized review."""
        trade = await self.uow.trades.get(id)
        if trade is None:
            raise NotFoundError(f"Trade with id {id} not found")
        review = await self.uow.trades.upsert_review(
            trade_id=id,
            content=dto.content,
            lesson_learned=dto.lesson_learned,
        )
        return {
            "id": review.id,
            "trade_id": review.trade_id,
            "content": review.content,
            "lesson_learned": review.lesson_learned,
            "created_at": review.created_at,
            "updated_at": review.updated_at,
        }

    # ------------------------------------------------------------------
    # Private validators
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_sl_tp(
        direction: str,
        entry_price: float,
        stop_loss: float | None,
        take_profit: float | None,
    ) -> None:
        """BR-07, BR-08, BR-09 — SL/TP position relative to entry price.

        BR-07 (long):  SL < entry_price
        BR-07 (short): SL > entry_price
        BR-08 (long):  TP > entry_price
        BR-08 (short): TP < entry_price
        BR-09:         SL and TP must be on opposite sides of entry_price
        """
        if stop_loss is not None:
            if direction == "long" and stop_loss >= entry_price:
                raise BusinessRuleError(
                    "Stop loss must be below entry price for long trades "
                    f"(entry: {entry_price}, sl: {stop_loss})"
                )
            if direction == "short" and stop_loss <= entry_price:
                raise BusinessRuleError(
                    "Stop loss must be above entry price for short trades "
                    f"(entry: {entry_price}, sl: {stop_loss})"
                )

        if take_profit is not None:
            if direction == "long" and take_profit <= entry_price:
                raise BusinessRuleError(
                    "Take profit must be above entry price for long trades "
                    f"(entry: {entry_price}, tp: {take_profit})"
                )
            if direction == "short" and take_profit >= entry_price:
                raise BusinessRuleError(
                    "Take profit must be below entry price for short trades "
                    f"(entry: {entry_price}, tp: {take_profit})"
                )

        if stop_loss is not None and take_profit is not None:
            sl_below = stop_loss < entry_price
            tp_below = take_profit < entry_price
            if sl_below == tp_below:
                raise BusinessRuleError(
                    "Stop loss and take profit must be on opposite sides of entry price "
                    f"(entry: {entry_price}, sl: {stop_loss}, tp: {take_profit})"
                )

    @staticmethod
    def _validate_exit_consistency(
        status: str,
        exit_price: float | None,
        exit_datetime: datetime | None,
    ) -> None:
        """BR-10: exit_price and exit_datetime must both be NULL or both set.

        When ``status='closed'``, both fields are required.
        When ``status='open'``, both must be null.
        """
        if status == "closed":
            if exit_price is None or exit_datetime is None:
                raise BusinessRuleError(
                    "exit_price and exit_datetime are required when status is 'closed'"
                )
        else:
            if exit_price is not None or exit_datetime is not None:
                raise BusinessRuleError(
                    "exit_price and exit_datetime must be null when status is 'open'"
                )

    @staticmethod
    def _validate_editable(trade: Trade) -> None:
        """BR-12: 30-day soft-lock on edits.

        If ``editable_until`` has passed, the trade cannot be modified.
        """
        if trade.editable_until is not None:
            if datetime.now(UTC).isoformat() > trade.editable_until:
                raise BusinessRuleError(
                    f"Trade with id {trade.id} is past its editable window "
                    f"(editable_until: {trade.editable_until})"
                )
