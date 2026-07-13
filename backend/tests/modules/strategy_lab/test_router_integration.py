"""Integration tests for the Strategy Lab API layer (PR #3).

Tests the full request–response cycle through the FastAPI test client.
Prerequisite data is created via the ``uow`` fixture (shared in-memory DB).
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models.account import Account
from app.models.asset import Asset
from app.models.catalogs import Market
from app.models.strategy import Strategy
from app.models.strategy_lab import Experiment, Run, StrategyVersion
from app.models.trade import Trade

# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
async def market(uow):
    m = Market(name="Forex")
    await uow.markets.add(m)
    return m


@pytest.fixture
async def account(uow):
    acc = Account(name="test_account")
    await uow.accounts.add(acc)
    return acc


@pytest.fixture
async def asset(uow, market):
    a = Asset(market_id=market.id, symbol="EURUSD", name="Euro/USD")
    await uow.assets.add(a)
    return a


@pytest.fixture
async def strategy(uow):
    s = Strategy(name="router_test_strat")
    await uow.strategies.add(s)
    return s


@pytest.fixture
async def strategy_version(uow, strategy):
    sv = StrategyVersion(
        strategy_id=strategy.id,
        version=1,
        parameters={"param_a": 0.5},
    )
    await uow.strategy_versions.add(sv)
    return sv


@pytest.fixture
async def experiment(uow):
    exp = Experiment(
        name="router_test_exp",
        description="API integration test",
        hypothesis="Hypothesis test",
    )
    await uow.experiments.add(exp)
    return exp


async def _create_closed_trade(uow, account, asset, direction, entry, exit_, qty=1.0):
    trade = Trade(
        account_id=account.id,
        asset_id=asset.id,
        direction=direction,
        status="closed",
        entry_price=entry,
        exit_price=exit_,
        quantity=qty,
        entry_datetime=datetime(2026, 1, 1, 0, 0, 0),
        exit_datetime=datetime(2026, 1, 2, 0, 0, 0),
        commission=0.0,
    )
    await uow.trades.add(trade)
    return trade


@pytest.fixture
async def winning_trades(uow, account, asset):
    """Profitable trades for run creation."""
    trades = []
    for i in range(3):
        t = await _create_closed_trade(
            uow, account, asset, "long", entry=100.0 + i, exit_=110.0 + i, qty=1.0
        )
        trades.append(t)
    return trades


@pytest.fixture
async def losing_trades(uow, account, asset):
    """Losing trades for baseline comparison."""
    trades = []
    for i in range(3):
        trade = Trade(
            account_id=account.id,
            asset_id=asset.id,
            direction="long",
            status="closed",
            entry_price=110.0 + i,
            exit_price=100.0 + i,
            quantity=1.0,
            entry_datetime=datetime(2026, 2, 10, 0, 0, 0),
            exit_datetime=datetime(2026, 2, 15, 0, 0, 0),
            commission=0.0,
        )
        await uow.trades.add(trade)
        trades.append(trade)
    return trades


# ======================================================================
# Strategy Version tests
# ======================================================================


@pytest.mark.asyncio
async def test_create_strategy_version(client, strategy):
    """POST /strategy-versions → 201 with version detail."""
    response = await client.post(
        "/api/strategy-lab/strategy-versions",
        json={
            "strategy_id": strategy.id,
            "parameters": {"sma_period": 20},
            "change_log": "Initial version",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["strategy_id"] == strategy.id
    assert data["version"] == 1
    assert data["parameters"] == {"sma_period": 20}
    assert data["change_log"] == "Initial version"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_strategy_versions(client, strategy, strategy_version):
    """GET /strategy-versions?strategy_id=X → 200 with array."""
    # Create a second version via API
    await client.post(
        "/api/strategy-lab/strategy-versions",
        json={
            "strategy_id": strategy.id,
            "parameters": {"sma_period": 50},
            "change_log": "Second version",
        },
    )

    # List
    response = await client.get(f"/api/strategy-lab/strategy-versions?strategy_id={strategy.id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) >= 2  # fixture version + API-created version


# ======================================================================
# Experiment tests
# ======================================================================


@pytest.mark.asyncio
async def test_create_experiment(client):
    """POST /experiments → 201 with experiment detail."""
    response = await client.post(
        "/api/strategy-lab/experiments",
        json={
            "name": "Integration Test Experiment",
            "description": "Testing API layer",
            "hypothesis": "Strategy X beats benchmark",
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "Integration Test Experiment"
    assert data["description"] == "Testing API layer"
    assert data["hypothesis"] == "Strategy X beats benchmark"
    assert data["status"] == "draft"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["run_count"] == 0


@pytest.mark.asyncio
async def test_list_experiments(client, experiment):
    """GET /experiments → 200 with array."""
    response = await client.get("/api/strategy-lab/experiments")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) >= 1
    # Verify our fixture experiment is in the list
    ids = [e["id"] for e in data]
    assert experiment.id in ids


@pytest.mark.asyncio
async def test_get_experiment(client, experiment, uow, strategy_version):
    """GET /experiments/{id} → 200 with run_count."""
    # Create a run for the experiment so run_count > 0
    run = Run(
        experiment_id=experiment.id,
        strategy_version_id=strategy_version.id,
        engine_version="1.0.0",
        dataset_snapshot_id="snap-test",
        parameters={},
        filters={},
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )
    await uow.runs.add(run)
    await uow.commit()

    response = await client.get(f"/api/strategy-lab/experiments/{experiment.id}")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["id"] == experiment.id
    assert data["name"] == experiment.name
    assert data["run_count"] == 1


@pytest.mark.asyncio
async def test_get_experiment_not_found(client):
    """GET /experiments/99999 → 404."""
    response = await client.get("/api/strategy-lab/experiments/99999")
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_delete_experiment_no_runs(client, experiment):
    """DELETE /experiments/{id} → 204 when no runs exist."""
    response = await client.delete(f"/api/strategy-lab/experiments/{experiment.id}")
    assert response.status_code == 204, response.text


@pytest.mark.asyncio
async def test_delete_experiment_with_runs(client, experiment, strategy_version, uow):
    """DELETE /experiments/{id} → 409 when runs still reference it."""
    run = Run(
        experiment_id=experiment.id,
        strategy_version_id=strategy_version.id,
        engine_version="1.0.0",
        dataset_snapshot_id="snap-del",
        parameters={},
        filters={},
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )
    await uow.runs.add(run)

    response = await client.delete(f"/api/strategy-lab/experiments/{experiment.id}")
    assert response.status_code == 409, response.text


# ======================================================================
# Run tests
# ======================================================================


@pytest.mark.asyncio
async def test_create_run(client, strategy_version, experiment):
    """POST /runs → 201 with full run + metrics."""
    response = await client.post(
        "/api/strategy-lab/runs",
        json={
            "experiment_id": experiment.id,
            "strategy_version_id": strategy_version.id,
            "filters": {
                "date_from": "2026-01-01T00:00:00",
                "date_to": "2026-01-31T00:00:00",
            },
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["experiment_id"] == experiment.id
    assert data["strategy_version_id"] == strategy_version.id
    assert data["status"] == "completed"
    assert data["engine_version"] is not None
    assert len(data["engine_version"]) > 0
    assert data["dataset_snapshot_id"] is not None
    assert data["baseline_run_id"] is None
    assert data["error_message"] is None
    assert "id" in data
    assert "created_at" in data
    assert "date_from" in data
    assert "date_to" in data
    assert isinstance(data["metrics"], list)
    # Metrics may be empty or populated depending on comparison
    assert "parameters" in data
    assert "filters" in data


@pytest.mark.asyncio
async def test_create_run_without_experiment(client, strategy_version):
    """POST /runs → 201 when experiment_id is None."""
    response = await client.post(
        "/api/strategy-lab/runs",
        json={
            "experiment_id": None,
            "strategy_version_id": strategy_version.id,
            "filters": {
                "date_from": "2026-01-01T00:00:00",
                "date_to": "2026-01-31T00:00:00",
            },
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["experiment_id"] is None
    assert data["status"] == "completed"


@pytest.mark.asyncio
async def test_create_run_duplicate(client, strategy_version, experiment):
    """POST /runs with duplicate config → 409."""
    body = {
        "strategy_version_id": strategy_version.id,
        "experiment_id": experiment.id,
        "filters": {
            "date_from": "2026-01-01T00:00:00",
            "date_to": "2026-01-31T00:00:00",
        },
    }

    # First run should succeed
    r1 = await client.post("/api/strategy-lab/runs", json=body)
    assert r1.status_code == 201, r1.text

    # Second identical run → 409 Conflict
    r2 = await client.post("/api/strategy-lab/runs", json=body)
    assert r2.status_code == 409, r2.text
    assert "duplicate" in r2.text.lower() or "Duplicate" in r2.text


@pytest.mark.asyncio
async def test_create_run_invalid_strategy_version(client, experiment):
    """POST /runs with non-existent strategy version → 404."""
    response = await client.post(
        "/api/strategy-lab/runs",
        json={
            "strategy_version_id": 99999,
            "experiment_id": experiment.id,
            "filters": {
                "date_from": "2026-01-01T00:00:00",
                "date_to": "2026-01-31T00:00:00",
            },
        },
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_get_run(client, strategy_version, experiment):
    """POST + GET /runs/{id} → 200 with full run + metrics."""
    create_resp = await client.post(
        "/api/strategy-lab/runs",
        json={
            "experiment_id": experiment.id,
            "strategy_version_id": strategy_version.id,
            "filters": {
                "date_from": "2026-01-01T00:00:00",
                "date_to": "2026-01-31T00:00:00",
            },
        },
    )
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/strategy-lab/runs/{run_id}")
    assert get_resp.status_code == 200, get_resp.text
    data = get_resp.json()
    assert data["id"] == run_id
    assert data["experiment_id"] == experiment.id
    assert data["strategy_version_id"] == strategy_version.id
    assert isinstance(data["metrics"], list)


@pytest.mark.asyncio
async def test_get_nonexistent_run(client):
    """GET /runs/99999 → 404."""
    response = await client.get("/api/strategy-lab/runs/99999")
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_list_runs(client, strategy_version, experiment):
    """GET /runs → 200 with array of runs."""
    # Create two runs
    for offset in range(2):
        await client.post(
            "/api/strategy-lab/runs",
            json={
                "experiment_id": experiment.id,
                "strategy_version_id": strategy_version.id,
                "filters": {
                    "date_from": "2026-01-01T00:00:00",
                    "date_to": f"2026-01-{15 + offset * 10:02d}T00:00:00",
                },
            },
        )

    response = await client.get("/api/strategy-lab/runs")
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data) >= 2


# ======================================================================
# Comparison tests
# ======================================================================


@pytest.mark.asyncio
async def test_compare_runs(
    client,
    uow,
    account,
    asset,
    strategy,
    experiment,
    winning_trades,
    losing_trades,
):
    """GET /runs/{id}/compare?baseline_id=X → 200 with ComparisonResult."""
    # Create strategy version
    sv_resp = await client.post(
        "/api/strategy-lab/strategy-versions",
        json={
            "strategy_id": strategy.id,
            "parameters": {},
            "change_log": "Comparison test",
        },
    )
    assert sv_resp.status_code == 201
    sv_id = sv_resp.json()["id"]

    # Baseline run uses losing trades (Feb dates)
    baseline_resp = await client.post(
        "/api/strategy-lab/runs",
        json={
            "experiment_id": experiment.id,
            "strategy_version_id": sv_id,
            "filters": {
                "date_from": "2026-02-01T00:00:00",
                "date_to": "2026-03-01T00:00:00",
            },
        },
    )
    assert baseline_resp.status_code == 201, baseline_resp.text
    baseline_id = baseline_resp.json()["id"]

    # Treatment run uses winning trades (Jan dates)
    treatment_resp = await client.post(
        "/api/strategy-lab/runs",
        json={
            "experiment_id": experiment.id,
            "strategy_version_id": sv_id,
            "filters": {
                "date_from": "2026-01-01T00:00:00",
                "date_to": "2026-02-01T00:00:00",
            },
        },
    )
    assert treatment_resp.status_code == 201, treatment_resp.text
    treatment_id = treatment_resp.json()["id"]

    # Compare
    compare_resp = await client.get(
        f"/api/strategy-lab/runs/{treatment_id}/compare?baseline_id={baseline_id}"
    )
    assert compare_resp.status_code == 200, compare_resp.text
    data = compare_resp.json()
    assert "run_a" in data
    assert "run_b" in data
    assert "results" in data
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert "metric_name" in result
    assert "diff_mean" in result
    assert "p_value" in result
    assert "effect_size" in result
    assert "ci_lower" in result
    assert "ci_upper" in result


@pytest.mark.asyncio
async def test_compare_runs_not_found(client, strategy_version, experiment):
    """GET /runs/{id}/compare when the baseline run does not exist → 404."""
    # Create a run
    run_resp = await client.post(
        "/api/strategy-lab/runs",
        json={
            "experiment_id": experiment.id,
            "strategy_version_id": strategy_version.id,
            "filters": {
                "date_from": "2026-01-01T00:00:00",
                "date_to": "2026-01-31T00:00:00",
            },
        },
    )
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # Compare against non-existent baseline
    compare_resp = await client.get(f"/api/strategy-lab/runs/{run_id}/compare?baseline_id=99999")
    assert compare_resp.status_code == 404, compare_resp.text
