"""Performance / load tests for the MT5 import pipeline.

Generates a multi-row CSV programmatically and measures preview + confirm
timing and memory usage. Marked with ``@pytest.mark.slow`` so they can be
skipped in daily runs.

Uses the ``client`` (AsyncClient) and ``uow`` fixtures from conftest.
"""

import time

import pytest
from httpx import AsyncClient

from app.models.account import Account
from app.models.asset import Asset
from app.models.catalogs import Market

pytestmark = pytest.mark.slow

# =========================================================================
# Helpers
# =========================================================================

CSV_HEADER = (
    "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice,"
    "CloseTime,ClosePrice,StopLoss,TakeProfit,Commission,Swap,"
    "Profit,Comment,Magic"
)


def _generate_csv(num_rows: int, start_ticket: int = 1) -> bytes:
    """Generate a multi-row MT5 CSV as bytes, all rows valid.

    Sets direction-aware SL/TP so both long and short rows pass BR-07/08/09:
    - long  (buy):  SL < entry_price, TP > entry_price (e.g. 1.080 / 1.090)
    - short (sell): SL > entry_price, TP < entry_price (e.g. 1.090 / 1.080)
    """
    lines = [CSV_HEADER]
    for i in range(num_rows):
        ticket = start_ticket + i
        direction = "buy" if i % 2 == 0 else "sell"
        # Direction-aware SL/TP to pass BR-07/08/09
        if direction == "buy":
            sl, tp = "1.08000", "1.09000"
        else:
            sl, tp = "1.09000", "1.08000"
        lines.append(
            f"{ticket},123456,EURUSD,{direction},0.10,"
            f"2026.01.15 10:00:00,1.08500,"
            f"2026.01.15 15:30:00,1.08800,"
            f"{sl},{tp},"
            f"-3.50,0.00,50.00,Performance test,101\n"
        )
    content = "\n".join(lines)
    return content.encode("utf-8-sig")


def _get_vm_rss_kb() -> int:
    """Read current RSS from /proc/self/status (Linux only).

    Returns 0 if unavailable (non-Linux or permission issue).
    """
    try:
        with open("/proc/self/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return int(parts[1])  # kB
    except (FileNotFoundError, OSError, ValueError, IndexError):
        pass
    return 0


async def _seed_perf_data(uow):
    """Seed the DB with one market, account, and asset for performance tests."""
    market = Market(name="forex")
    await uow.markets.add(market)

    account = Account(name="123456", broker="PerfBroker", base_currency="USD")
    await uow.accounts.add(account)

    asset = Asset(symbol="EURUSD", market_id=market.id, name="EUR/USD")
    await uow.assets.add(asset)


# =========================================================================
# Performance Tests
# =========================================================================


@pytest.mark.slow
@pytest.mark.asyncio
async def test_import_bulk_throughput(client: AsyncClient, uow):
    """Import a substantial number of rows: measure preview + confirm timing.

    1. Generate a multi-row CSV programmatically
    2. POST /api/imports/mt5/preview → assert within 30s
    3. POST /api/imports/mt5/confirm → assert all imported
    4. Check memory usage (coarse — read /proc/self/status VmRSS)
    5. Verify DB has expected trade count
    """
    await _seed_perf_data(uow)

    # Use 1000 rows for SQLite performance — PostgreSQL would be 10-50x faster
    row_count = 1000
    csv_bytes = _generate_csv(row_count)
    assert len(csv_bytes) > 0

    # ── Preview ──────────────────────────────────────────────────────
    rss_before_preview = _get_vm_rss_kb()

    t0 = time.monotonic()
    preview_resp = await client.post(
        "/api/imports/mt5/preview",
        files={"file": ("perf.csv", csv_bytes, "text/csv")},
    )
    preview_elapsed = time.monotonic() - t0

    assert preview_resp.status_code == 200, f"Preview failed: {preview_resp.text}"
    preview = preview_resp.json()
    assert preview["total_rows"] == row_count
    assert preview["valid_rows"] == row_count
    assert preview["invalid_rows"] == 0

    # Verify no trades created during preview
    _, total = await uow.trades.list(page=1, page_size=10000)
    assert total == 0

    rss_after_preview = _get_vm_rss_kb()

    # ── Confirm ──────────────────────────────────────────────────────
    rss_before_confirm = _get_vm_rss_kb()

    t1 = time.monotonic()
    confirm_resp = await client.post(
        "/api/imports/mt5/confirm",
        files={"file": ("perf.csv", csv_bytes, "text/csv")},
    )
    confirm_elapsed = time.monotonic() - t1

    assert confirm_resp.status_code == 200, f"Confirm failed: {confirm_resp.text}"
    confirm = confirm_resp.json()
    assert confirm["total_rows"] == row_count
    assert confirm["imported_rows"] == row_count
    assert confirm["skipped_rows"] == 0
    assert confirm["error_rows"] == 0

    # Verify DB has all trades
    _, total = await uow.trades.list(page=1, page_size=10000)
    assert total == row_count

    rss_after_confirm = _get_vm_rss_kb()

    # -- Reporting (not assertions) ------------------------------------
    print(f"\n[PERF] Preview {row_count} rows: {preview_elapsed:.2f}s")
    print(f"[PERF] Confirm {row_count} rows: {confirm_elapsed:.2f}s")
    print(f"[PERF] RSS before preview: {rss_before_preview} kB")
    print(f"[PERF] RSS after preview:  {rss_after_preview} kB")
    print(f"[PERF] RSS after confirm:  {rss_after_confirm} kB")

    # Assert timing within limits.
    # NOTE: SQLite + savepoints (begin_nested()) is inherently slow. With
    # PostgreSQL the same workload is 10-50x faster. The generous 120s limit
    # accounts for SQLite's nested-transaction overhead.
    assert preview_elapsed < 30, f"Preview took {preview_elapsed:.2f}s (limit: 30s)"
    assert confirm_elapsed < 120, f"Confirm took {confirm_elapsed:.2f}s (limit: 120s)"

    # Assert memory under ~200 MB (200000 kB) delta
    if rss_after_confirm > 0 and rss_before_confirm > 0:
        mem_delta = rss_after_confirm - rss_before_confirm
        print(f"[PERF] Memory delta: {mem_delta} kB")
        # Coarse check: RSS should not grow by >200 MB from baseline
        assert mem_delta < 200_000, f"Memory grew by {mem_delta} kB (limit: 200000 kB)"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_preview_bulk_no_side_effects(client: AsyncClient, uow):
    """Preview a large CSV — verify no trades are created in DB."""
    await _seed_perf_data(uow)

    row_count = 1000
    csv_bytes = _generate_csv(row_count)

    t0 = time.monotonic()
    preview_resp = await client.post(
        "/api/imports/mt5/preview",
        files={"file": ("perf.csv", csv_bytes, "text/csv")},
    )
    elapsed = time.monotonic() - t0

    assert preview_resp.status_code == 200
    preview = preview_resp.json()
    assert preview["total_rows"] == row_count
    assert preview["valid_rows"] == row_count

    # Assert no trades created
    _, total = await uow.trades.list(page=1, page_size=10000)
    assert total == 0

    print(f"\n[PERF] Preview {row_count} rows (no confirm): {elapsed:.2f}s")
    # Preview is pure parsing + validation — no DB writes. Should be fast even on SQLite.
    assert elapsed < 30, f"Preview-only took {elapsed:.2f}s (limit: 30s)"
