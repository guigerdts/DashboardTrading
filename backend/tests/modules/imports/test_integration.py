"""Integration tests for the full MT5 import E2E pipeline.

Tests the complete flow: upload → preview → confirm → verify DB state.
Uses the ``client`` (AsyncClient) for HTTP requests and the ``uow`` fixture
for direct DB verification.
"""

import pytest
from httpx import AsyncClient

from app.models.account import Account
from app.models.asset import Asset
from app.models.catalogs import Market

# =========================================================================
# Helpers
# =========================================================================

CSV_HEADER = (
    "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice,"
    "CloseTime,ClosePrice,StopLoss,TakeProfit,Commission,Swap,"
    "Profit,Comment,Magic"
)


def _make_csv(rows: int = 3, start_ticket: int = 1000) -> bytes:
    """Generate a valid MT5 CSV with *rows* trades, as bytes."""
    lines = [CSV_HEADER]
    for i in range(rows):
        ticket = start_ticket + i
        lines.append(
            f"{ticket},123456,EURUSD,buy,0.10,"
            f"2026.01.10 08:00:00,1.10000,"
            f"2026.01.10 16:00:00,1.10500,"
            f"1.09500,1.11000,"
            f"-3.50,0.00,50.00,Import test,\n"
        )
    return "\n".join(lines).encode("utf-8-sig")


def _make_csv_from_rows(rows: list[list[str]]) -> bytes:
    """Build a CSV from a list of field-value rows (as bytes).

    Each element of *rows* is a list of column values in order:
    Ticket, Login, Symbol, Direction, Volume, OpenTime, OpenPrice,
    CloseTime, ClosePrice, StopLoss, TakeProfit, Commission, Swap,
    Profit, Comment, Magic.
    """
    header = CSV_HEADER + "\n"
    lines = [header]
    for row in rows:
        lines.append(",".join(row) + "\n")
    return "".join(lines).encode("utf-8-sig")


async def _seed_data(uow):
    """Seed minimal catalogs + one account + one asset for E2E tests.

    Returns (account, asset).
    """
    market = Market(name="forex")
    await uow.markets.add(market)

    account = Account(name="123456", broker="TestBroker", base_currency="USD")
    await uow.accounts.add(account)

    asset = Asset(symbol="EURUSD", market_id=market.id, name="EUR/USD")
    await uow.assets.add(asset)

    return account, asset


async def _seed_data_two_accounts(uow):
    """Seed two accounts with matching assets for cross-account tests.

    Returns (account1, account2, asset).
    """
    market = Market(name="forex")
    await uow.markets.add(market)

    account1 = Account(name="ACC001", broker="TestBroker", base_currency="USD")
    account2 = Account(name="ACC002", broker="TestBroker", base_currency="USD")
    await uow.accounts.add(account1)
    await uow.accounts.add(account2)

    asset = Asset(symbol="EURUSD", market_id=market.id, name="EUR/USD")
    await uow.assets.add(asset)

    return account1, account2, asset


# =========================================================================
# E2E Integration Tests
# =========================================================================


class TestE2EHappyPath:
    """Full E2E: upload → preview → confirm → verify DB."""

    @pytest.mark.asyncio
    async def test_e2e_happy_path(self, client: AsyncClient, uow):
        """Complete happy-path E2E flow with DB verification.

        1. Create account + asset + market fixtures
        2. POST /api/imports/mt5/preview → 200, all valid, no trades in DB
        3. POST /api/imports/mt5/confirm → 200, all imported
        4. Query DB directly to verify trades exist with correct data
        """
        await _seed_data(uow)
        csv_bytes = _make_csv(rows=3, start_ticket=5000)

        # ── Preview ──────────────────────────────────────────────────
        preview_resp = await client.post(
            "/api/imports/mt5/preview",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert preview_resp.status_code == 200
        preview = preview_resp.json()
        assert preview["total_rows"] == 3
        assert preview["valid_rows"] == 3
        assert preview["invalid_rows"] == 0
        assert all(r["status"] == "valid" for r in preview["rows"])

        # Assert no trades in DB yet (preview is read-only)
        _, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 0

        # ── Confirm ──────────────────────────────────────────────────
        confirm_resp = await client.post(
            "/api/imports/mt5/confirm",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert confirm_resp.status_code == 200
        confirm = confirm_resp.json()
        assert confirm["total_rows"] == 3
        assert confirm["imported_rows"] == 3
        assert confirm["skipped_rows"] == 0
        assert confirm["error_rows"] == 0

        # ── Verify DB directly ──────────────────────────────────────
        trades, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 3

        # broker_ticket is set correctly
        tickets = {t.broker_ticket for t in trades}
        for i in range(3):
            assert str(5000 + i) in tickets

        # Direction is correct (all buy → long)
        for t in trades:
            assert t.direction in ("long", "short")

        # Quantities match
        for t in trades:
            assert t.quantity == 0.10

        # broker_ticket is not None on any trade
        for t in trades:
            assert t.broker_ticket is not None


class TestE2EIdempotent:
    """Re-importing the same CSV: first call imports, second skips all."""

    @pytest.mark.asyncio
    async def test_e2e_idempotent(self, client: AsyncClient, uow):
        """First confirm imports all rows; second confirm skips all with trade_ids."""
        await _seed_data(uow)
        csv_bytes = _make_csv(rows=2, start_ticket=7000)

        # First import — all new
        resp1 = await client.post(
            "/api/imports/mt5/confirm",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["imported_rows"] == 2
        assert data1["skipped_rows"] == 0

        first_ids = [r["trade_id"] for r in data1["rows"] if r["status"] == "imported"]

        # Second import with same CSV — all should be skipped
        resp2 = await client.post(
            "/api/imports/mt5/confirm",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["imported_rows"] == 0
        assert data2["skipped_rows"] == 2
        for row in data2["rows"]:
            assert row["status"] == "skipped"
            assert row["trade_id"] in first_ids

        # Verify no duplicate trades in DB
        _, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 2


class TestE2EPartialImport:
    """CSV with a mix of valid and invalid rows."""

    @pytest.mark.asyncio
    async def test_e2e_partial_import(self, client: AsyncClient, uow):
        """CSV with 4 valid + 1 invalid -> 4 imported, 1 error.

        Invalid row has empty symbol (missing symbol). Only valid rows
        should appear in DB.
        """
        await _seed_data(uow)

        # Row 3 has empty symbol (invalid)
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
                "Import test",
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
                "Import test",
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
                "TKT103",
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
                "TKT104",
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
        csv_bytes = _make_csv_from_rows(rows_data)

        # Confirm — valid rows imported, invalid row errored
        resp = await client.post(
            "/api/imports/mt5/confirm",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 5
        assert data["imported_rows"] == 4
        assert data["error_rows"] == 1
        assert data["skipped_rows"] == 0

        # Row 3 (1-indexed) should be the error
        error_rows = [r for r in data["rows"] if r["status"] == "error"]
        assert len(error_rows) == 1
        assert error_rows[0]["row_index"] == 3

        # Query DB — only 4 trades exist
        _, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 4

        # Invalid row ticket should NOT be in DB
        all_trades, _ = await uow.trades.list(page=1, page_size=1000)
        db_tickets = {t.broker_ticket for t in all_trades}
        assert "TKT102" not in db_tickets


class TestE2EPreviewNoSideEffects:
    """Preview does not write to DB; confirm works after preview."""

    @pytest.mark.asyncio
    async def test_e2e_preview_no_side_effects(self, client: AsyncClient, uow):
        """Calling preview leaves DB unchanged; confirm after preview works."""
        await _seed_data(uow)
        csv_bytes = _make_csv(rows=2, start_ticket=9000)

        # Verify trades table count is 0 before
        _, total_before = await uow.trades.list(page=1, page_size=1000)
        assert total_before == 0

        # Preview → verify trades table unchanged
        preview_resp = await client.post(
            "/api/imports/mt5/preview",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert preview_resp.status_code == 200

        _, total_after_preview = await uow.trades.list(page=1, page_size=1000)
        assert total_after_preview == 0

        # Confirm — trades should be created
        confirm_resp = await client.post(
            "/api/imports/mt5/confirm",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert confirm_resp.status_code == 200
        data = confirm_resp.json()
        assert data["imported_rows"] == 2

        _, total_after_confirm = await uow.trades.list(page=1, page_size=1000)
        assert total_after_confirm == 2


class TestE2EDuplicateTicketSameAccount:
    """CSV-internal duplicate (same account, same broker_ticket)."""

    @pytest.mark.asyncio
    async def test_e2e_duplicate_ticket_same_account_skipped(self, client: AsyncClient, uow):
        """Two rows with same (account, broker_ticket) in one CSV.

        The validator catches CSV-internal duplicates and marks the second
        occurrence as invalid. First row imported, second row errored (not skipped),
        because the validator rejects it before it reaches the import phase.
        """
        await _seed_data(uow)

        rows_data = [
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
                "Import test",
                "",
            ],
            [
                "DUP001",
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
        csv_bytes = _make_csv_from_rows(rows_data)

        resp = await client.post(
            "/api/imports/mt5/confirm",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_rows"] == 2
        assert data["imported_rows"] == 1
        # Second row is a CSV-internal duplicate → flagged by validator as invalid → "error"
        assert data["error_rows"] == 1

        # First row imported
        first_row = data["rows"][0]
        assert first_row["status"] == "imported"
        assert first_row["trade_id"] is not None

        # Second row is error (CSV-internal duplicate detected by validator)
        second_row = data["rows"][1]
        assert second_row["status"] == "error"
        assert any("Duplicate" in e for e in second_row["errors"])

        # Only 1 trade in DB
        _, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 1


class TestE2ESameTicketDifferentAccounts:
    """Same broker_ticket on different accounts is allowed."""

    @pytest.mark.asyncio
    async def test_e2e_same_ticket_different_accounts_ok(self, client: AsyncClient, uow):
        """Two rows with same broker_ticket but different accounts → both imported.

        The UNIQUE constraint is per (account_id, broker_ticket), so different
        accounts can have the same ticket number.
        """
        await _seed_data_two_accounts(uow)

        rows_data = [
            [
                "TKT001",
                "ACC001",
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
                "TKT001",
                "ACC002",
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
        csv_bytes = _make_csv_from_rows(rows_data)

        resp = await client.post(
            "/api/imports/mt5/confirm",
            files={"file": ("test.csv", csv_bytes, "text/csv")},
        )
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_rows"] == 2
        assert data["imported_rows"] == 2
        assert data["error_rows"] == 0
        assert data["skipped_rows"] == 0

        # Both rows imported
        for row in data["rows"]:
            assert row["status"] == "imported"
            assert row["trade_id"] is not None

        # 2 trades in DB (different accounts)
        trades, total = await uow.trades.list(page=1, page_size=1000)
        assert total == 2

        # Verify different account_ids
        account_ids = {t.account_id for t in trades}
        assert len(account_ids) == 2
