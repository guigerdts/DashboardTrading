"""Full stack integration tests for the analytics module.

Uses the per-test DB with seeded Account, Asset, and Trade records,
then verifies all 6 analytics endpoints return EXACTLY computed metrics.
"""

from datetime import UTC, datetime

import pytest

from app.models.account import Account
from app.models.asset import Asset
from app.models.trade import Trade


@pytest.mark.asyncio
async def test_summary_known_trades(uow, client):
    """5 known trades with manually computed summary metrics."""
    # ── Seed accounts & assets ──────────────────────────────────────
    account = Account(name="Test Account")
    eur = Asset(market_id=1, symbol="EURUSD")
    gbp = Asset(market_id=1, symbol="GBPUSD")
    await uow.accounts.add(account)
    await uow.assets.add(eur)
    await uow.assets.add(gbp)

    # ── 5 trades with known PnLs ────────────────────────────────────
    # 1: long +10, 2: long -5, 3: short +8, 4: long +3, 5: short -2
    trades_data = [
        Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=110.0,
            quantity=1.0,  # PnL = +10
            entry_datetime=datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
            exit_datetime=datetime(2026, 1, 2, tzinfo=UTC).isoformat(),
        ),
        Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=95.0,
            quantity=1.0,  # PnL = -5
            entry_datetime=datetime(2026, 1, 3, tzinfo=UTC).isoformat(),
            exit_datetime=datetime(2026, 1, 4, tzinfo=UTC).isoformat(),
        ),
        Trade(
            account_id=account.id,
            asset_id=gbp.id,
            direction="short",
            status="closed",
            entry_price=100.0,
            exit_price=92.0,
            quantity=1.0,  # PnL = +8 (short)
            entry_datetime=datetime(2026, 1, 5, tzinfo=UTC).isoformat(),
            exit_datetime=datetime(2026, 1, 6, tzinfo=UTC).isoformat(),
        ),
        Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=103.0,
            quantity=1.0,  # PnL = +3
            entry_datetime=datetime(2026, 1, 7, tzinfo=UTC).isoformat(),
            exit_datetime=datetime(2026, 1, 8, tzinfo=UTC).isoformat(),
        ),
        Trade(
            account_id=account.id,
            asset_id=gbp.id,
            direction="short",
            status="closed",
            entry_price=100.0,
            exit_price=102.0,
            quantity=1.0,  # PnL = -2
            entry_datetime=datetime(2026, 1, 9, tzinfo=UTC).isoformat(),
            exit_datetime=datetime(2026, 1, 10, tzinfo=UTC).isoformat(),
        ),
    ]
    for t in trades_data:
        await uow.trades.add(t)
    await uow.commit()

    # ── Manually computed expected values ───────────────────────────
    # PnLs: +10, -5, +8, +3, -2
    # net_pnl = 10 - 5 + 8 + 3 - 2 = 14
    # gross_profit = 10 + 8 + 3 = 21
    # gross_loss = -5 + -2 = -7
    # wins = 3, losses = 2
    # win_rate = 3/5 = 0.6
    # profit_factor = 21 / 7 = 3.0
    # expectancy = (0.6 * 7.0) - (0.4 * 3.5) = 4.2 - 1.4 = 2.8
    #   avg_win = 21/3 = 7.0, avg_loss = 7/2 = 3.5

    resp = await client.get("/api/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 5
    assert data["performance"]["net_pnl"] == 14.0
    assert data["performance"]["gross_profit"] == 21.0
    assert data["performance"]["gross_loss"] == -7.0
    assert data["performance"]["win_rate"] == 0.6
    assert data["performance"]["profit_factor"] == 3.0
    assert data["performance"]["expectancy"] == 2.8
    assert data["performance"]["avg_win"] == 7.0
    assert data["performance"]["avg_loss"] == 3.5


@pytest.mark.asyncio
async def test_equity_curve_point_by_point(uow, client):
    """Equity curve matches hand-computed cumulative PnL."""
    account = Account(name="Test Account")
    eur = Asset(market_id=1, symbol="EURUSD")
    await uow.accounts.add(account)
    await uow.assets.add(eur)

    # 3 trades in order: +10, -4, +5 → equity: 10, 6, 11
    trades = [
        Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=110.0,
            quantity=1.0,
            entry_datetime="2026-01-01T00:00:00",
            exit_datetime="2026-01-02T00:00:00",
        ),
        Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=96.0,
            quantity=1.0,
            entry_datetime="2026-01-03T00:00:00",
            exit_datetime="2026-01-04T00:00:00",
        ),
        Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=105.0,
            quantity=1.0,
            entry_datetime="2026-01-05T00:00:00",
            exit_datetime="2026-01-06T00:00:00",
        ),
    ]
    for t in trades:
        await uow.trades.add(t)
    await uow.commit()

    resp = await client.get("/api/analytics/equity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 3
    curve = data["equity_curve"]
    assert len(curve) == 3
    assert curve[0]["equity"] == 10.0
    assert curve[1]["equity"] == 6.0
    assert curve[2]["equity"] == 11.0


@pytest.mark.asyncio
async def test_breakdown_two_assets_five_trades(uow, client):
    """Breakdown by asset produces correct per-asset metrics."""
    account = Account(name="Test Account")
    eur = Asset(market_id=1, symbol="EURUSD")
    gbp = Asset(market_id=2, symbol="GBPUSD")
    await uow.accounts.add(account)
    await uow.assets.add(eur)
    await uow.assets.add(gbp)

    # EURUSD: 3 trades → +10, -5, +3 → net +8
    # GBPUSD: 2 trades → +8, -2 → net +6
    trades = [
        Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=110.0,
            quantity=1.0,
            entry_datetime="2026-01-01T00:00:00",
            exit_datetime="2026-01-02T00:00:00",
        ),
        Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=95.0,
            quantity=1.0,
            entry_datetime="2026-01-03T00:00:00",
            exit_datetime="2026-01-04T00:00:00",
        ),
        Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=103.0,
            quantity=1.0,
            entry_datetime="2026-01-05T00:00:00",
            exit_datetime="2026-01-06T00:00:00",
        ),
        Trade(
            account_id=account.id,
            asset_id=gbp.id,
            direction="short",
            status="closed",
            entry_price=100.0,
            exit_price=92.0,
            quantity=1.0,
            entry_datetime="2026-01-07T00:00:00",
            exit_datetime="2026-01-08T00:00:00",
        ),
        Trade(
            account_id=account.id,
            asset_id=gbp.id,
            direction="short",
            status="closed",
            entry_price=100.0,
            exit_price=102.0,
            quantity=1.0,
            entry_datetime="2026-01-09T00:00:00",
            exit_datetime="2026-01-10T00:00:00",
        ),
    ]
    for t in trades:
        await uow.trades.add(t)
    await uow.commit()

    resp = await client.get("/api/analytics/breakdown/asset")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 5

    symbols = {a["symbol"] for a in data["assets"]}
    assert symbols == {"EURUSD", "GBPUSD"}

    for asset in data["assets"]:
        if asset["symbol"] == "EURUSD":
            assert asset["trade_count"] == 3
            assert asset["net_pnl"] == 8.0  # +10-5+3
        elif asset["symbol"] == "GBPUSD":
            assert asset["trade_count"] == 2
            assert asset["net_pnl"] == 6.0  # +8-2


@pytest.mark.asyncio
async def test_empty_db_returns_empty_metrics(uow, client):
    """All endpoints return empty/zero metrics when no trades exist."""
    resp = await client.get("/api/analytics/summary")
    assert resp.json()["total_trades"] == 0

    resp = await client.get("/api/analytics/equity")
    assert resp.json()["equity_curve"] == []

    resp = await client.get("/api/analytics/performance")
    assert resp.json()["total_trades"] == 0

    resp = await client.get("/api/analytics/breakdown/asset")
    assert resp.json()["assets"] == []

    resp = await client.get("/api/analytics/breakdown/direction")
    assert resp.json()["total_trades"] == 0

    resp = await client.get("/api/analytics/breakdown/market")
    assert resp.json()["markets"] == []


@pytest.mark.asyncio
async def test_single_trade(uow, client):
    """A single winning trade returns correct metrics."""
    account = Account(name="Test Account")
    eur = Asset(market_id=1, symbol="EURUSD")
    await uow.accounts.add(account)
    await uow.assets.add(eur)

    trade = Trade(
        account_id=account.id,
        asset_id=eur.id,
        direction="long",
        status="closed",
        entry_price=100.0,
        exit_price=120.0,
        quantity=2.0,  # PnL = +40
        entry_datetime="2026-01-01T00:00:00",
        exit_datetime="2026-01-02T00:00:00",
    )
    await uow.trades.add(trade)
    await uow.commit()

    resp = await client.get("/api/analytics/summary")
    data = resp.json()
    assert data["total_trades"] == 1
    assert data["performance"]["net_pnl"] == 40.0
    assert data["performance"]["win_rate"] == 1.0


@pytest.mark.asyncio
async def test_all_wins(uow, client):
    """All winning trades produce profit_factor=None (no losses)."""
    account = Account(name="Test Account")
    eur = Asset(market_id=1, symbol="EURUSD")
    await uow.accounts.add(account)
    await uow.assets.add(eur)

    for i in range(3):
        t = Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=110.0 + i,
            quantity=1.0,
            entry_datetime=f"2026-01-{i + 1:02d}T00:00:00",
            exit_datetime=f"2026-01-{i + 2:02d}T00:00:00",
        )
        await uow.trades.add(t)
    await uow.commit()

    resp = await client.get("/api/analytics/summary")
    data = resp.json()
    assert data["performance"]["profit_factor"] is None
    assert data["performance"]["win_rate"] == 1.0


@pytest.mark.asyncio
async def test_all_losses(uow, client):
    """All losing trades produce profit_factor=None (no profits)."""
    account = Account(name="Test Account")
    eur = Asset(market_id=1, symbol="EURUSD")
    await uow.accounts.add(account)
    await uow.assets.add(eur)

    for i in range(2):
        t = Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=90.0 - i,
            quantity=1.0,
            entry_datetime=f"2026-01-{i + 1:02d}T00:00:00",
            exit_datetime=f"2026-01-{i + 2:02d}T00:00:00",
        )
        await uow.trades.add(t)
    await uow.commit()

    resp = await client.get("/api/analytics/summary")
    data = resp.json()
    # When gross_profit == 0 and gross_loss != 0, profit_factor = 0.0
    assert data["performance"]["profit_factor"] == 0.0
    assert data["performance"]["win_rate"] == 0.0


@pytest.mark.asyncio
@pytest.mark.slow
async def test_performance_1000_trades(uow, client):
    """1000 trades complete quickly (performance regression guard)."""
    import time

    account = Account(name="Test Account")
    eur = Asset(market_id=1, symbol="EURUSD")
    await uow.accounts.add(account)
    await uow.assets.add(eur)

    for i in range(1000):
        exit_pnl = 100.0 + (i % 50 - 25)  # mix wins and losses
        t = Trade(
            account_id=account.id,
            asset_id=eur.id,
            direction="long",
            status="closed",
            entry_price=100.0,
            exit_price=exit_pnl,
            quantity=1.0,
            entry_datetime=f"2026-01-{i % 28 + 1:02d}T00:00:00",
            exit_datetime=f"2026-01-{(i % 28) + 2:02d}T00:00:00",
        )
        await uow.trades.add(t)
    await uow.commit()

    start = time.monotonic()
    resp = await client.get("/api/analytics/summary")
    elapsed = time.monotonic() - start

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 1000
    assert elapsed < 5.0, f"1000 trades took {elapsed:.2f}s (expected < 5s)"
