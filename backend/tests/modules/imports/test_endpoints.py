"""Endpoint tests for the imports module — MT5 CSV upload, preview, and confirm.

Uses the ``client`` (AsyncClient) and ``uow`` fixtures from conftest.
The ``client`` fixture overrides ``get_db`` to use the in-memory test database.
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


def _make_csv(rows: int = 3) -> bytes:
    """Generate a valid MT5 CSV with *rows* identical trades, as bytes."""
    lines = [CSV_HEADER]
    for i in range(1, rows + 1):
        lines.append(
            f"{1000 + i},123456,EURUSD,buy,0.10,"
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


async def _seed_endpoint_data(uow):
    """Seed minimal catalogs + one account + one asset for endpoint tests.

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
# POST /api/imports/mt5/preview
# =========================================================================


@pytest.mark.asyncio
async def test_preview_valid_csv_returns_200(client: AsyncClient, uow):
    """``POST /api/imports/mt5/preview`` with valid CSV returns 200 with PreviewResponse."""
    await _seed_endpoint_data(uow)
    csv_bytes = _make_csv(rows=3)

    response = await client.post(
        "/api/imports/mt5/preview",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_rows" in data
    assert "valid_rows" in data
    assert "invalid_rows" in data
    assert "rows" in data
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 3
    assert data["invalid_rows"] == 0
    assert len(data["rows"]) == 3
    assert all(r["status"] == "valid" for r in data["rows"])


@pytest.mark.asyncio
async def test_preview_invalid_csv_returns_200_with_errors(client: AsyncClient, uow):
    """``POST /api/imports/mt5/preview`` with bad data returns 200 with error rows."""
    await _seed_endpoint_data(uow)

    # Row 1: valid, Row 2: missing symbol, Row 3: missing ticket
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
    csv_bytes = _make_csv_from_rows(rows_data)

    response = await client.post(
        "/api/imports/mt5/preview",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert data["valid_rows"] == 1
    assert data["invalid_rows"] == 2

    # Row 1 is valid, Row 2 has missing symbol, Row 3 has missing ticket
    assert data["rows"][0]["status"] == "valid"
    assert data["rows"][1]["status"] == "invalid"
    assert data["rows"][2]["status"] == "invalid"
    assert any("Missing symbol" in e for e in data["rows"][1]["errors"])
    assert any("Missing broker ticket" in e for e in data["rows"][2]["errors"])


@pytest.mark.asyncio
async def test_preview_empty_file_returns_200(client: AsyncClient, uow):
    """``POST /api/imports/mt5/preview`` with empty CSV returns 200, total_rows=0."""
    await _seed_endpoint_data(uow)

    # CSV with header only
    csv_bytes = CSV_HEADER.encode("utf-8-sig") + b"\n"

    response = await client.post(
        "/api/imports/mt5/preview",
        files={"file": ("empty.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 0
    assert data["valid_rows"] == 0
    assert data["invalid_rows"] == 0
    assert data["rows"] == []


@pytest.mark.asyncio
async def test_preview_without_file_returns_422(client: AsyncClient):
    """``POST /api/imports/mt5/preview`` with no file returns 422."""
    response = await client.post("/api/imports/mt5/preview")
    assert response.status_code == 422


# =========================================================================
# POST /api/imports/mt5/confirm
# =========================================================================


@pytest.mark.asyncio
async def test_confirm_valid_csv_imports_trades(client: AsyncClient, uow):
    """``POST /api/imports/mt5/confirm`` imports trades and returns ImportResult."""
    await _seed_endpoint_data(uow)
    csv_bytes = _make_csv(rows=3)

    response = await client.post(
        "/api/imports/mt5/confirm",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_rows" in data
    assert "imported_rows" in data
    assert "skipped_rows" in data
    assert "error_rows" in data
    assert "rows" in data
    assert data["total_rows"] == 3
    assert data["imported_rows"] == 3
    assert data["skipped_rows"] == 0
    assert data["error_rows"] == 0

    # Verify trades exist in DB
    trades, total = await uow.trades.list(page=1, page_size=1000)
    assert total == 3
    for t in trades:
        assert t.broker_ticket is not None


@pytest.mark.asyncio
async def test_confirm_idempotency(client: AsyncClient, uow):
    """Re-importing the same CSV: first call imports N, second skips all N."""
    await _seed_endpoint_data(uow)
    csv_bytes = _make_csv(rows=2)

    # First import — all new
    response1 = await client.post(
        "/api/imports/mt5/confirm",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["imported_rows"] == 2
    assert data1["skipped_rows"] == 0

    # Second import — all should be skipped
    response2 = await client.post(
        "/api/imports/mt5/confirm",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["imported_rows"] == 0
    assert data2["skipped_rows"] == 2
    for row in data2["rows"]:
        assert row["status"] == "skipped"
        assert row["trade_id"] is not None


@pytest.mark.asyncio
async def test_confirm_partial_import(client: AsyncClient, uow):
    """CSV with 4 valid + 1 invalid -> 4 imported, 1 error."""
    await _seed_endpoint_data(uow)

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
    csv_bytes = _make_csv_from_rows(rows_data)

    response = await client.post(
        "/api/imports/mt5/confirm",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 5
    assert data["imported_rows"] == 4
    assert data["error_rows"] == 1
    assert data["skipped_rows"] == 0

    # Row 3 (1-indexed) should be the error
    error_rows = [r for r in data["rows"] if r["status"] == "error"]
    assert len(error_rows) == 1
    assert error_rows[0]["row_index"] == 3

    # 4 trades in DB
    _, total = await uow.trades.list(page=1, page_size=1000)
    assert total == 4


@pytest.mark.asyncio
async def test_confirm_empty_file(client: AsyncClient, uow):
    """``POST /api/imports/mt5/confirm`` with empty CSV returns 200, 0 imported."""
    await _seed_endpoint_data(uow)

    csv_bytes = CSV_HEADER.encode("utf-8-sig") + b"\n"

    response = await client.post(
        "/api/imports/mt5/confirm",
        files={"file": ("empty.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 0
    assert data["imported_rows"] == 0
    assert data["skipped_rows"] == 0
    assert data["error_rows"] == 0


@pytest.mark.asyncio
async def test_confirm_with_non_mt5_csv_returns_422(client: AsyncClient, uow):
    """``POST /api/imports/mt5/confirm`` with CSV missing required columns returns 422."""
    await _seed_endpoint_data(uow)

    # CSV missing required columns (no Ticket, Symbol, etc.)
    bad_csv = "Name,Age,Country\nAlice,30,US\nBob,25,UK\n"
    csv_bytes = bad_csv.encode("utf-8-sig")

    response = await client.post(
        "/api/imports/mt5/confirm",
        files={"file": ("bad.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_confirm_uses_service_correctly(client: AsyncClient, uow):
    """``POST /api/imports/mt5/confirm`` returns correct response structure."""
    await _seed_endpoint_data(uow)
    csv_bytes = _make_csv(rows=1)

    response = await client.post(
        "/api/imports/mt5/confirm",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()

    # Top-level fields
    assert isinstance(data["total_rows"], int)
    assert isinstance(data["imported_rows"], int)
    assert isinstance(data["skipped_rows"], int)
    assert isinstance(data["error_rows"], int)
    assert isinstance(data["rows"], list)

    # Verify the response matches ImportResult schema exactly
    assert set(data.keys()) == {"total_rows", "imported_rows", "skipped_rows", "error_rows", "rows"}

    # Check row-level structure
    assert len(data["rows"]) == 1
    row = data["rows"][0]
    assert isinstance(row["row_index"], int)
    assert isinstance(row["broker_ticket"], str) or row["broker_ticket"] is None
    assert row["status"] in ("imported", "skipped", "error")
    assert isinstance(row["errors"], list)
    assert isinstance(row["warnings"], list)
    assert "trade_id" in row
    expected_keys = {"row_index", "broker_ticket", "status", "trade_id", "errors", "warnings"}
    assert set(row.keys()) == expected_keys


@pytest.mark.asyncio
async def test_confirm_preview_consistent_counts(client: AsyncClient, uow):
    """Preview and confirm should report consistent row counts for valid CSV."""
    await _seed_endpoint_data(uow)
    csv_bytes = _make_csv(rows=5)

    # Preview
    preview_resp = await client.post(
        "/api/imports/mt5/preview",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )
    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["total_rows"] == 5
    assert preview["valid_rows"] == 5

    # Confirm
    confirm_resp = await client.post(
        "/api/imports/mt5/confirm",
        files={"file": ("test.csv", csv_bytes, "text/csv")},
    )
    assert confirm_resp.status_code == 200
    confirm = confirm_resp.json()
    assert confirm["total_rows"] == 5
    assert confirm["imported_rows"] == 5
