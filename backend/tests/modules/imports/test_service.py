"""Service tests for ImportService — preview + confirm pipeline.

Uses the ``uow`` fixture from conftest (in-memory SQLite, transaction-scoped).
"""

from io import BytesIO
from unittest import mock

import pytest
from fastapi import UploadFile

from app.models.account import Account
from app.models.asset import Asset
from app.models.catalogs import Market
from app.models.trade import Trade
from app.modules.imports.context import ImportContext
from app.modules.imports.schemas import ImportResult, PreviewResponse
from app.modules.imports.service import ImportService

# =========================================================================
# Helpers
# =========================================================================


def _make_csv(content: str, filename: str = "test.csv") -> UploadFile:
    """Build a FastAPI UploadFile from CSV string content."""
    return UploadFile(filename=filename, file=BytesIO(content.encode("utf-8-sig")))


def _sample_csv(rows: int = 3) -> str:
    """Generate a valid MT5 CSV with *rows* identical trades."""
    header = (
        "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice,"
        "CloseTime,ClosePrice,StopLoss,TakeProfit,Commission,Swap,"
        "Profit,Comment,Magic\n"
    )
    lines = [header]
    for i in range(1, rows + 1):
        lines.append(
            f"{1000 + i},123456,EURUSD,buy,0.10,"
            f"2026.01.10 08:00:00,1.10000,"
            f"2026.01.10 16:00:00,1.10500,"
            f"1.09500,1.11000,"
            f"-3.50,0.00,50.00,Import test,\n"
        )
    return "".join(lines)


def _make_csv_from_rows(rows: list[list[str]]) -> str:
    """Build a CSV string from a list of field-value rows.

    Each element of *rows* is a list of column values in order:
    Ticket, Login, Symbol, Direction, Volume, OpenTime, OpenPrice,
    CloseTime, ClosePrice, StopLoss, TakeProfit, Commission, Swap,
    Profit, Comment, Magic.
    """
    header = (
        "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice,"
        "CloseTime,ClosePrice,StopLoss,TakeProfit,Commission,Swap,"
        "Profit,Comment,Magic\n"
    )
    lines = [header]
    for row in rows:
        lines.append(",".join(row) + "\n")
    return "".join(lines)


async def _seed_import_data(uow):
    """Seed minimal catalogs + one account + one asset for import tests.

    Returns (account, asset).
    """
    market = Market(name="forex")
    await uow.markets.add(market)

    account = Account(name="123456", broker="TestBroker", base_currency="USD")
    await uow.accounts.add(account)

    asset = Asset(symbol="EURUSD", market_id=market.id, name="EUR/USD")
    await uow.assets.add(asset)

    return account, asset


# =========================================================================
# Preview tests
# =========================================================================


class TestImportServicePreview:
    """ImportService.preview() — read-only validation."""

    @pytest.mark.asyncio
    async def test_preview_returns_without_writing(self, uow):
        """Preview returns PreviewResponse and does NOT create trades."""
        await _seed_import_data(uow)
        svc = ImportService(uow)
        csv = _make_csv(_sample_csv(rows=2))

        result = await svc.preview(csv)

        assert isinstance(result, PreviewResponse)
        assert result.total_rows == 2
        assert result.valid_rows == 2
        assert result.invalid_rows == 0

        # No trades created
        _, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 0

    @pytest.mark.asyncio
    async def test_preview_no_side_effects(self, uow):
        """DB state is completely unchanged after preview."""
        await _seed_import_data(uow)
        svc = ImportService(uow)

        # Count trades before
        before, _ = await uow.trades.list(page=1, page_size=1000)
        before_count = len(before)

        csv = _make_csv(_sample_csv(rows=3))
        await svc.preview(csv)

        # Count trades after — should be identical
        after, after_total = await uow.trades.list(page=1, page_size=1000)
        assert after_total == before_count

    @pytest.mark.asyncio
    async def test_preview_invalid_rows_reported(self, uow):
        """Preview reports invalid rows with correct status and errors."""
        await _seed_import_data(uow)
        svc = ImportService(uow)

        # CSV: row 2 has empty symbol, row 3 has missing ticket
        rows_data = [
            [
                "1001",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
            [
                "1002",
                "123456",
                "",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
            [
                "",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
        ]
        csv = _make_csv(_make_csv_from_rows(rows_data))

        result = await svc.preview(csv)

        assert result.total_rows == 3
        assert result.valid_rows == 1
        assert result.invalid_rows == 2
        assert result.rows[0].status == "valid"
        assert result.rows[1].status == "invalid"
        assert result.rows[2].status == "invalid"
        assert any("Missing symbol" in e for e in result.rows[1].errors)
        assert any("Missing broker ticket" in e for e in result.rows[2].errors)


# =========================================================================
# Confirm tests
# =========================================================================


class TestImportServiceConfirm:
    """ImportService.confirm() — full pipeline with persistence."""

    @pytest.mark.asyncio
    async def test_confirm_imports_valid_rows(self, uow):
        """Confirm imports all valid rows into the DB."""
        await _seed_import_data(uow)
        svc = ImportService(uow)
        csv = _make_csv(_sample_csv(rows=3))

        result = await svc.confirm(csv)

        assert isinstance(result, ImportResult)
        assert result.total_rows == 3
        assert result.imported_rows == 3
        assert result.skipped_rows == 0
        assert result.error_rows == 0

        # Verify trades exist in DB
        trades, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 3
        for t in trades:
            assert t.broker_ticket is not None

    @pytest.mark.asyncio
    async def test_confirm_idempotency(self, uow):
        """Re-importing the same CSV: first call imports N, second skips all N."""
        acc, _ = await _seed_import_data(uow)
        svc = ImportService(uow)
        csv_content = _sample_csv(rows=2)

        # First import — all new
        result1 = await svc.confirm(_make_csv(csv_content))
        assert result1.imported_rows == 2
        assert result1.skipped_rows == 0

        # Second import with a fresh UploadFile — all should be skipped
        svc2 = ImportService(uow)
        result2 = await svc2.confirm(_make_csv(csv_content))
        assert result2.imported_rows == 0
        assert result2.skipped_rows == 2
        for row in result2.rows:
            assert row.status == "skipped"
            assert row.trade_id is not None

    @pytest.mark.asyncio
    async def test_confirm_partial_import(self, uow):
        """CSV with 4 valid + 1 invalid -> 4 imported, 1 error."""
        await _seed_import_data(uow)
        svc = ImportService(uow)

        # Row 3 has empty symbol (invalid)
        rows_data = [
            [
                "TKT001",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "Import test",
                "",
            ],
            [
                "TKT002",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "Import test",
                "",
            ],
            [
                "TKT003",
                "123456",
                "",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
            [
                "TKT004",
                "123456",
                "EURUSD",
                "sell",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.09500",
                "1.10500",
                "1.09000",
                "-3.50",
                "0.00",
                "-50.00",
                "Import test",
                "",
            ],
            [
                "TKT005",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "Import test",
                "",
            ],
        ]
        csv = _make_csv(_make_csv_from_rows(rows_data))

        result = await svc.confirm(csv)

        assert result.total_rows == 5
        assert result.imported_rows == 4
        assert result.error_rows == 1
        assert result.skipped_rows == 0

        # Row 3 (index 2 in 0-based) should be the error
        error_rows = [r for r in result.rows if r.status == "error"]
        assert len(error_rows) == 1
        assert error_rows[0].row_index == 3  # 1-indexed

        # 4 trades in DB
        _, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 4

    @pytest.mark.asyncio
    async def test_confirm_savepoint_isolation(self, uow):
        """One row triggering BR violation does not block other rows."""
        acc, asset = await _seed_import_data(uow)
        svc = ImportService(uow)

        # Row 2: long trade with SL >= entry_price -> BR-07 violation
        # Buy (long) at 1.10000 with stop_loss at 1.10500 -> SL above entry = BR violation
        rows_data = [
            [
                "TKT010",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "OK",
                "",
            ],
            [
                "TKT020",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.10500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "BR_BAD",
                "",
            ],
            # ^ SL (1.10500) >= entry (1.10000) for long -> BR-07 violation
            [
                "TKT030",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "OK",
                "",
            ],
        ]
        csv = _make_csv(_make_csv_from_rows(rows_data))

        result = await svc.confirm(csv)

        assert result.total_rows == 3
        assert result.imported_rows == 2
        assert result.error_rows == 1

        # Row 2 (1-indexed) should have BR error
        error_rows = [r for r in result.rows if r.status == "error"]
        assert len(error_rows) == 1
        assert error_rows[0].row_index == 2
        assert any("Stop loss" in e for e in error_rows[0].errors)

        # 2 trades in DB (rows 1 and 3)
        _, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 2

    @pytest.mark.asyncio
    async def test_confirm_fresh_context(self, uow):
        """Confirm creates a fresh ImportContext — does not reuse preview state."""
        await _seed_import_data(uow)
        svc = ImportService(uow)
        csv = _make_csv(_sample_csv(rows=1))

        with mock.patch.object(ImportContext, "from_db") as mock_from_db:
            # Return empty context so rows become invalid (not imported)
            mock_from_db.return_value = ImportContext()
            await svc.confirm(csv)
            # Verify from_db was called exactly once during confirm
            mock_from_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_empty_csv(self, uow):
        """Empty CSV returns 0 imported rows without error."""
        await _seed_import_data(uow)
        svc = ImportService(uow)

        # CSV with header only
        header = (
            "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice,"
            "CloseTime,ClosePrice,StopLoss,TakeProfit,Commission,Swap,"
            "Profit,Comment,Magic\n"
        )
        csv = _make_csv(header)

        result = await svc.confirm(csv)

        assert result.total_rows == 0
        assert result.imported_rows == 0
        assert result.skipped_rows == 0
        assert result.error_rows == 0

    @pytest.mark.asyncio
    async def test_import_mixed_valid_invalid_skipped(self, uow):
        """Mix of valid, invalid, and DB-duplicate rows."""
        acc, asset = await _seed_import_data(uow)

        # Seed one existing trade with ticket "DUP001"
        existing = Trade(
            account_id=acc.id,
            asset_id=asset.id,
            direction="long",
            status="closed",
            entry_price=1.1000,
            quantity=0.10,
            entry_datetime="2026-01-01T00:00:00+00:00",
            exit_price=1.1050,
            exit_datetime="2026-01-02T00:00:00+00:00",
            broker_ticket="DUP001",
            commission=0.0,
            swap_fees=0.0,
        )
        await uow.trades.add(existing)
        await uow._session.flush()  # ensure existing trade is visible to queries

        svc = ImportService(uow)

        # CSV: 5 rows — 3 valid, 1 invalid (missing symbol), 1 duplicate
        rows_data = [
            [
                "TKT100",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "OK",
                "",
            ],
            [
                "TKT101",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "OK",
                "",
            ],
            [
                "TKT102",
                "123456",
                "",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ],
            [
                "DUP001",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "OK",
                "",
            ],
            [
                "TKT103",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "OK",
                "",
            ],
        ]
        csv = _make_csv(_make_csv_from_rows(rows_data))

        result = await svc.confirm(csv)

        assert result.total_rows == 5
        assert result.imported_rows == 3
        assert result.skipped_rows == 1
        assert result.error_rows == 1

        # Row 3 (invalid: missing symbol)
        error_rows = [r for r in result.rows if r.status == "error"]
        assert len(error_rows) == 1
        assert error_rows[0].row_index == 3

        # Row 4 (duplicate)
        skipped_rows = [r for r in result.rows if r.status == "skipped"]
        assert len(skipped_rows) == 1
        assert skipped_rows[0].row_index == 4
        assert skipped_rows[0].trade_id == existing.id

        # Total trades in DB: 1 existing + 3 new = 4
        _, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 4

    @pytest.mark.asyncio
    async def test_import_correctly_sets_broker_ticket(self, uow):
        """Imported trades have the correct broker_ticket value."""
        acc, _ = await _seed_import_data(uow)
        svc = ImportService(uow)

        rows_data = [
            [
                "ALPHA",
                "123456",
                "EURUSD",
                "buy",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.10500",
                "1.09500",
                "1.11000",
                "-3.50",
                "0.00",
                "50.00",
                "Import test",
                "",
            ],
            [
                "BETA",
                "123456",
                "EURUSD",
                "sell",
                "0.10",
                "2026.01.10 08:00:00",
                "1.10000",
                "2026.01.10 16:00:00",
                "1.09500",
                "1.10500",
                "1.09000",
                "-3.50",
                "0.00",
                "-50.00",
                "Import test",
                "",
            ],
        ]
        csv = _make_csv(_make_csv_from_rows(rows_data))

        result = await svc.confirm(csv)

        assert result.imported_rows == 2

        # Fetch trades and check broker_ticket
        trades, _ = await uow.trades.list(page=1, page_size=1000)
        tickets = {t.broker_ticket for t in trades}
        assert "ALPHA" in tickets
        assert "BETA" in tickets

        # Verify row-level result has correct broker_ticket
        for row in result.rows:
            if row.status == "imported":
                assert row.broker_ticket in ("ALPHA", "BETA")
