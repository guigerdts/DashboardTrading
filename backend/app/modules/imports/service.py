"""ImportService — orchestrates the full import pipeline.

Transient: parses, validates, and imports MT5 trades without storing the CSV.
"""

import logging
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import BusinessRuleError
from app.db.unit_of_work import UnitOfWork
from app.modules.imports.context import ImportContext
from app.modules.imports.normalizers.mt5 import Mt5Normalizer
from app.modules.imports.parsers.mt5 import Mt5Parser
from app.modules.imports.schemas import (
    ImportResult,
    NormalizedTrade,
    PreviewResponse,
    RowResult,
)
from app.modules.imports.validator import ImportValidator
from app.modules.trades.schemas import TradeCreate
from app.modules.trades.service import TradeService

IMPORT_BATCH_SIZE = 500
logger = logging.getLogger(__name__)


class ImportService:
    """Orchestrates the MT5 import pipeline: parse -> normalize -> validate -> persist."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.parser = Mt5Parser()
        self.normalizer = Mt5Normalizer()
        self.validator = ImportValidator()
        self.trade_service = TradeService(uow)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def preview(self, file) -> PreviewResponse:
        """Preview: parse + normalize + validate. Read-only. Never writes."""
        raw = await self.parser.parse(file)
        normalized = self.normalizer.normalize(raw)
        ctx = await ImportContext.from_db(self.uow)
        results = self.validator.validate(normalized, ctx)

        valid_count = sum(1 for r in results if r.status == "valid")
        return PreviewResponse(
            total_rows=len(results),
            valid_rows=valid_count,
            invalid_rows=len(results) - valid_count,
            rows=results,
        )

    async def confirm(self, file) -> ImportResult:
        """Confirm: re-execute full pipeline, import valid rows via TradeService.

        Creates a FRESH ImportContext — does NOT reuse preview state.
        Each valid row: savepoint -> flush -> batch commit.
        """
        # Re-execute full pipeline from scratch
        raw = await self.parser.parse(file)
        normalized = self.normalizer.normalize(raw)
        ctx = await ImportContext.from_db(self.uow)  # FRESH context
        validation = self.validator.validate(normalized, ctx)

        # Gather valid rows for import
        valid_indices = {r.row_index for r in validation if r.status == "valid"}
        valid_trades = [n for n in normalized if n.row_index in valid_indices]

        results_map: dict[int, RowResult] = {}

        # Seed with validation results (invalid rows stay as-is)
        row_order: list[int] = []
        for v in validation:
            row_order.append(v.row_index)
            if v.status == "invalid":
                results_map[v.row_index] = RowResult(
                    row_index=v.row_index,
                    broker_ticket=v.broker_ticket,
                    status="error",
                    errors=v.errors,
                    warnings=v.warnings,
                )

        # Import valid rows in batches
        for batch_start in range(0, len(valid_trades), IMPORT_BATCH_SIZE):
            batch = valid_trades[batch_start : batch_start + IMPORT_BATCH_SIZE]

            for trade_row in batch:
                result = await self._import_one(trade_row, ctx)
                results_map[trade_row.row_index] = result

            await self.uow.commit()

        # Build final result preserving original row order
        rows = [results_map[i] for i in row_order]

        imported = sum(1 for r in rows if r.status == "imported")
        skipped = sum(1 for r in rows if r.status == "skipped")
        errors = sum(1 for r in rows if r.status == "error")

        return ImportResult(
            total_rows=len(rows),
            imported_rows=imported,
            skipped_rows=skipped,
            error_rows=errors,
            rows=rows,
        )

    # ------------------------------------------------------------------
    # Per-row import with savepoint isolation
    # ------------------------------------------------------------------

    async def _import_one(self, trade_row: NormalizedTrade, ctx: ImportContext) -> RowResult:
        """Import a single validated trade row with savepoint isolation."""
        # Resolve account from ImportContext
        account = ctx.accounts_by_name.get(trade_row.account_name)
        if account is None:
            return RowResult(
                row_index=trade_row.row_index,
                broker_ticket=trade_row.broker_ticket,
                status="error",
                errors=[f"Account '{trade_row.account_name}' not resolved"],
            )

        # Check for existing duplicate by broker_ticket
        if trade_row.broker_ticket:
            existing = await self.uow.trades.get_by_ticket(account.id, trade_row.broker_ticket)
            if existing:
                return RowResult(
                    row_index=trade_row.row_index,
                    broker_ticket=trade_row.broker_ticket,
                    status="skipped",
                    trade_id=existing.id,
                    warnings=[f"Already imported as trade #{existing.id}"],
                )

        # Resolve asset — first asset matching the symbol
        asset_list = ctx.assets_by_symbol.get(trade_row.symbol)
        if not asset_list:
            return RowResult(
                row_index=trade_row.row_index,
                broker_ticket=trade_row.broker_ticket,
                status="error",
                errors=[f"Asset '{trade_row.symbol}' not resolved"],
            )
        asset = asset_list[0]

        # Parse ISO datetime strings from NormalizedTrade to datetime objects
        # TradeCreate expects datetime objects, not ISO strings
        entry_datetime = datetime.fromisoformat(trade_row.entry_datetime)
        exit_datetime = (
            datetime.fromisoformat(trade_row.exit_datetime) if trade_row.exit_datetime else None
        )

        # Build TradeCreate DTO
        dto = TradeCreate(
            account_id=account.id,
            asset_id=asset.id,
            direction=trade_row.direction,
            status="closed" if trade_row.exit_datetime else "open",
            entry_price=trade_row.entry_price,
            quantity=trade_row.quantity,
            entry_datetime=entry_datetime,
            exit_price=trade_row.exit_price,
            exit_datetime=exit_datetime,
            stop_loss=trade_row.stop_loss,
            take_profit=trade_row.take_profit,
            commission=abs(trade_row.commission or 0),
            swap_fees=abs(trade_row.swap_fees or 0),
            risk_amount=trade_row.risk_amount,
            notes_override=trade_row.notes_override,
        )

        # Savepoint-isolated import
        try:
            async with self.uow._session.begin_nested():
                trade = await self.trade_service.create(dto)
                # Set broker_ticket after creation (not part of TradeCreate)
                trade.broker_ticket = trade_row.broker_ticket

            return RowResult(
                row_index=trade_row.row_index,
                broker_ticket=trade_row.broker_ticket,
                status="imported",
                trade_id=trade.id,
            )
        except BusinessRuleError as e:
            return RowResult(
                row_index=trade_row.row_index,
                broker_ticket=trade_row.broker_ticket,
                status="error",
                errors=[str(e)],
            )
        except IntegrityError:
            # UNIQUE constraint on broker_ticket (race condition)
            existing = await self.uow.trades.get_by_ticket(account.id, trade_row.broker_ticket)
            if existing:
                return RowResult(
                    row_index=trade_row.row_index,
                    broker_ticket=trade_row.broker_ticket,
                    status="skipped",
                    trade_id=existing.id,
                )
            return RowResult(
                row_index=trade_row.row_index,
                broker_ticket=trade_row.broker_ticket,
                status="error",
                errors=["Database constraint violation"],
            )
        except Exception:
            logger.exception("Unexpected error importing row %d", trade_row.row_index)
            return RowResult(
                row_index=trade_row.row_index,
                broker_ticket=trade_row.broker_ticket,
                status="error",
                errors=["Unexpected error during import"],
            )
