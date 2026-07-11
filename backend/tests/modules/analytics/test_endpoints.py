"""httpx endpoint tests for the analytics module.

Seeds trades in the per-test DB via the client's POST /api/trades endpoint,
then verifies all 6 analytics endpoints return 200 with expected shapes.
"""

import pytest

from app.models.account import Account
from app.models.asset import Asset

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _seed_trade(**overrides) -> dict:
    """POST a closed trade via the trades API and return the response JSON."""
    payload = {
        "account_id": 1,
        "asset_id": 1,
        "direction": "long",
        "status": "closed",
        "entry_price": 100.0,
        "quantity": 1.0,
        "entry_datetime": "2026-01-01T00:00:00",
        "exit_price": 110.0,
        "exit_datetime": "2026-01-02T00:00:00",
    }
    payload.update(overrides)
    return payload


# The FastAPI test client uses an in-memory DB with empty tables.
# We need to seed Account and Asset in the DB so FK constraints pass.
# Since the conftest only provides the client, we use the db_session fixture
# via the `client` fixture's override. For endpoint tests that need seed data,
# we create the required FK references directly via the uow fixture.


@pytest.mark.asyncio
async def test_summary_200(client):
    """``GET /api/analytics/summary`` returns 200."""
    resp = await client.get("/api/analytics/summary")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_equity_200(client):
    """``GET /api/analytics/equity`` returns 200."""
    resp = await client.get("/api/analytics/equity")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_performance_200(client):
    """``GET /api/analytics/performance`` returns 200."""
    resp = await client.get("/api/analytics/performance")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_breakdown_asset_200(client):
    """``GET /api/analytics/breakdown/asset`` returns 200."""
    resp = await client.get("/api/analytics/breakdown/asset")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_breakdown_direction_200(client):
    """``GET /api/analytics/breakdown/direction`` returns 200."""
    resp = await client.get("/api/analytics/breakdown/direction")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_breakdown_market_200(client):
    """``GET /api/analytics/breakdown/market`` returns 200."""
    resp = await client.get("/api/analytics/breakdown/market")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_empty_db_returns_zero_values(client):
    """All endpoints return 200 with zero values when DB is empty."""
    summary = (await client.get("/api/analytics/summary")).json()
    assert summary["total_trades"] == 0
    assert summary["performance"]["net_pnl"] == 0.0

    equity = (await client.get("/api/analytics/equity")).json()
    assert equity["total_trades"] == 0
    assert equity["equity_curve"] == []

    perf = (await client.get("/api/analytics/performance")).json()
    assert perf["total_trades"] == 0

    asset_bd = (await client.get("/api/analytics/breakdown/asset")).json()
    assert asset_bd["total_trades"] == 0
    assert asset_bd["assets"] == []

    dir_bd = (await client.get("/api/analytics/breakdown/direction")).json()
    assert dir_bd["total_trades"] == 0

    mkt_bd = (await client.get("/api/analytics/breakdown/market")).json()
    assert mkt_bd["total_trades"] == 0
    assert mkt_bd["markets"] == []


@pytest.mark.asyncio
async def test_account_id_and_date_filters(client):
    """Endpoints accept account_id and date filter query params."""
    resp = await client.get("/api/analytics/summary", params={"account_id": 1})
    assert resp.status_code == 200

    resp = await client.get(
        "/api/analytics/summary",
        params={"date_from": "2026-01-01T00:00:00", "date_to": "2026-12-31T00:00:00"},
    )
    assert resp.status_code == 200

    resp = await client.get("/api/analytics/equity", params={"account_id": 1})
    assert resp.status_code == 200

    resp = await client.get("/api/analytics/performance", params={"account_id": 1})
    assert resp.status_code == 200

    resp = await client.get("/api/analytics/breakdown/asset", params={"account_id": 1})
    assert resp.status_code == 200

    resp = await client.get("/api/analytics/breakdown/direction", params={"account_id": 1})
    assert resp.status_code == 200

    resp = await client.get("/api/analytics/breakdown/market", params={"account_id": 1})
    assert resp.status_code == 200

    # Risk analytics
    resp = await client.get("/api/analytics/risk-metrics", params={"account_id": 1})
    assert resp.status_code == 200

    resp = await client.get("/api/analytics/correlation", params={"account_id": 1})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_seeded_summary_has_values(client, uow):
    """With seeded trades, summary returns computed metrics."""
    # Seed account and asset
    account = Account(name="Test Account")
    asset = Asset(market_id=1, symbol="EURUSD")
    await uow.accounts.add(account)
    await uow.assets.add(asset)
    await uow.commit()

    # Seed a closed trade via API
    trade_payload = _seed_trade(
        account_id=account.id,
        asset_id=asset.id,
    )
    await client.post("/api/trades", json=trade_payload)

    resp = await client.get("/api/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 1
    assert data["performance"]["net_pnl"] == 10.0  # (110-100)*1


@pytest.mark.asyncio
async def test_openapi_schema_includes_analytics(client):
    """OpenAPI schema lists all analytics endpoints including new ones."""
    schema = (await client.get("/openapi.json")).json()
    paths = schema["paths"]
    assert "/api/analytics/summary" in paths
    assert "/api/analytics/equity" in paths
    assert "/api/analytics/performance" in paths
    assert "/api/analytics/breakdown/asset" in paths
    assert "/api/analytics/breakdown/direction" in paths
    assert "/api/analytics/breakdown/market" in paths
    # New endpoints
    assert "/api/analytics/breakdown/strategies" in paths
    assert "/api/analytics/breakdown/setups" in paths
    assert "/api/analytics/breakdown/tags" in paths
    assert "/api/analytics/breakdown/mistakes" in paths
    assert "/api/analytics/distribution/r" in paths
    assert "/api/analytics/heatmap" in paths
    # Rolling / Performance / Compare
    assert "/api/analytics/rolling" in paths
    assert "/api/analytics/performance/by-period" in paths
    assert "/api/analytics/performance/compare" in paths
    # Risk analytics
    assert "/api/analytics/risk-metrics" in paths
    assert "/api/analytics/exposure/by-asset" in paths
    assert "/api/analytics/exposure/by-session" in paths
    assert "/api/analytics/exposure/by-strategy" in paths
    assert "/api/analytics/correlation" in paths


# =========================================================================
# New endpoint tests (Phase 4)
# =========================================================================


@pytest.mark.asyncio
async def test_breakdown_strategies_200(client):
    """``GET /api/analytics/breakdown/strategies`` returns 200."""
    resp = await client.get("/api/analytics/breakdown/strategies")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_breakdown_setups_200(client):
    """``GET /api/analytics/breakdown/setups`` returns 200."""
    resp = await client.get("/api/analytics/breakdown/setups")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_breakdown_tags_200(client):
    """``GET /api/analytics/breakdown/tags`` returns 200."""
    resp = await client.get("/api/analytics/breakdown/tags")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_breakdown_mistakes_200(client):
    """``GET /api/analytics/breakdown/mistakes`` returns 200."""
    resp = await client.get("/api/analytics/breakdown/mistakes")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_r_distribution_200(client):
    """``GET /api/analytics/distribution/r`` returns 200."""
    resp = await client.get("/api/analytics/distribution/r")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_heatmap_200(client):
    """``GET /api/analytics/heatmap`` returns 200."""
    resp = await client.get("/api/analytics/heatmap")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_risk_metrics_200(client):
    """``GET /api/analytics/risk-metrics`` returns 200."""
    resp = await client.get("/api/analytics/risk-metrics")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_exposure_by_asset_200(client):
    """``GET /api/analytics/exposure/by-asset`` returns 200."""
    resp = await client.get("/api/analytics/exposure/by-asset")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_exposure_by_session_200(client):
    """``GET /api/analytics/exposure/by-session`` returns 200."""
    resp = await client.get("/api/analytics/exposure/by-session")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_exposure_by_strategy_200(client):
    """``GET /api/analytics/exposure/by-strategy`` returns 200."""
    resp = await client.get("/api/analytics/exposure/by-strategy")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_correlation_200(client):
    """``GET /api/analytics/correlation`` returns 200."""
    resp = await client.get("/api/analytics/correlation")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_new_endpoints_empty_db(client):
    """All new endpoints return correct empty shapes."""
    strategies = (await client.get("/api/analytics/breakdown/strategies")).json()
    assert strategies["items"] == []

    setups = (await client.get("/api/analytics/breakdown/setups")).json()
    assert setups["items"] == []

    tags = (await client.get("/api/analytics/breakdown/tags")).json()
    assert tags["items"] == []

    mistakes = (await client.get("/api/analytics/breakdown/mistakes")).json()
    assert mistakes["items"] == []

    dist = (await client.get("/api/analytics/distribution/r")).json()
    assert dist["buckets"] == []
    assert dist["total_trades"] == 0

    heatmap = (await client.get("/api/analytics/heatmap")).json()
    assert heatmap["cells"] == []

    # Risk analytics
    risk = (await client.get("/api/analytics/risk-metrics")).json()
    assert risk["max_drawdown"] == 0.0
    assert risk["drawdown_pct"] == 0.0
    assert risk["avg_holding_time_days"] == 0.0
    assert risk["kelly_fraction"] == 0.0

    exp_asset = (await client.get("/api/analytics/exposure/by-asset")).json()
    assert exp_asset == []

    exp_session = (await client.get("/api/analytics/exposure/by-session")).json()
    assert exp_session == []

    exp_strategy = (await client.get("/api/analytics/exposure/by-strategy")).json()
    assert exp_strategy == []

    corr = (await client.get("/api/analytics/correlation")).json()
    assert corr["assets"] == []
    assert corr["matrix"] == []


@pytest.mark.asyncio
async def test_summary_includes_new_fields(client, uow):
    """Summary response includes total_trades_all and total_open_trades."""
    from app.models.account import Account
    from app.models.asset import Asset

    account = Account(name="Test Account")
    asset = Asset(market_id=1, symbol="EURUSD")
    await uow.accounts.add(account)
    await uow.assets.add(asset)

    # Create one open and one closed trade
    from datetime import UTC, datetime

    from app.models.trade import Trade

    closed = Trade(
        account_id=account.id,
        asset_id=asset.id,
        direction="long",
        status="closed",
        entry_price=100.0,
        exit_price=110.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        exit_datetime=datetime(2026, 1, 2, tzinfo=UTC).isoformat(),
    )
    open_trade = Trade(
        account_id=account.id,
        asset_id=asset.id,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
    )
    await uow.trades.add(closed)
    await uow.trades.add(open_trade)
    await uow.commit()

    resp = await client.get("/api/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 1
    assert data["total_trades_all"] == 2
    assert data["total_open_trades"] == 1


@pytest.mark.asyncio
async def test_summary_still_has_existing_fields(client, uow):
    """Summary response includes all existing fields (regression guard)."""
    from datetime import UTC, datetime

    from app.models.account import Account
    from app.models.asset import Asset
    from app.models.trade import Trade

    account = Account(name="Test Account")
    asset = Asset(market_id=1, symbol="EURUSD")
    await uow.accounts.add(account)
    await uow.assets.add(asset)

    trade = Trade(
        account_id=account.id,
        asset_id=asset.id,
        direction="long",
        status="closed",
        entry_price=100.0,
        exit_price=110.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        exit_datetime=datetime(2026, 1, 2, tzinfo=UTC).isoformat(),
    )
    await uow.trades.add(trade)
    await uow.commit()

    resp = await client.get("/api/analytics/summary")
    data = resp.json()
    # Existing fields
    assert "total_trades" in data
    assert "performance" in data
    assert "risk" in data
    assert "net_pnl" in data["performance"]
    assert "gross_profit" in data["performance"]
    assert "gross_loss" in data["performance"]
    assert "win_rate" in data["performance"]
    assert "profit_factor" in data["performance"]
    assert "expectancy" in data["performance"]
    assert "avg_r_multiple" in data["performance"]
    # New fields
    assert "total_trades_all" in data
    assert "total_open_trades" in data


# =========================================================================
# Rolling endpoint tests
# =========================================================================


@pytest.mark.asyncio
async def test_rolling_endpoint(client):
    """``GET /api/analytics/rolling`` returns 200 with valid data."""
    resp = await client.get("/api/analytics/rolling", params={"window_size": 30})
    assert resp.status_code == 200
    data = resp.json()
    assert "window_size" in data
    assert "points" in data
    assert data["window_size"] == 30
    # Empty DB → points is empty array
    assert data["points"] == []


@pytest.mark.asyncio
async def test_rolling_endpoint_invalid_window(client):
    """window_size < 10 or > 200 → 422."""
    resp = await client.get("/api/analytics/rolling", params={"window_size": 5})
    assert resp.status_code == 422

    resp = await client.get("/api/analytics/rolling", params={"window_size": 250})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rolling_endpoint_default_window(client):
    """No window_size param → default 30."""
    resp = await client.get("/api/analytics/rolling")
    assert resp.status_code == 200
    assert resp.json()["window_size"] == 30


# =========================================================================
# Performance by period endpoint tests
# =========================================================================


@pytest.mark.asyncio
async def test_performance_by_period_endpoint(client):
    """``GET /api/analytics/performance/by-period`` returns 200."""
    resp = await client.get("/api/analytics/performance/by-period", params={"group_by": "month"})
    assert resp.status_code == 200
    data = resp.json()
    assert "records" in data
    assert data["records"] == []


@pytest.mark.asyncio
async def test_performance_by_period_default(client):
    """Default group_by is 'month'."""
    resp = await client.get("/api/analytics/performance/by-period")
    assert resp.status_code == 200


# =========================================================================
# Compare periods endpoint tests
# =========================================================================


@pytest.mark.asyncio
async def test_compare_periods_endpoint(client):
    """``GET /api/analytics/performance/compare`` returns 200 with two periods."""
    resp = await client.get(
        "/api/analytics/performance/compare",
        params={
            "period_a_from": "2026-01-01T00:00:00",
            "period_a_to": "2026-06-30T00:00:00",
            "period_b_from": "2026-07-01T00:00:00",
            "period_b_to": "2026-12-31T00:00:00",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "period_a" in data
    assert "period_b" in data
    assert "delta" in data
    assert "delta_percent" in data
    # Empty DB → trade_count = 0
    assert data["period_a"]["trade_count"] == 0
    assert data["period_b"]["trade_count"] == 0
