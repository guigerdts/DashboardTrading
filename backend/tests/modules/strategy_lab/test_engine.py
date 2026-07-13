"""Tests for Strategy Lab Engine (PR #2).

Covers:
- ``get_engine_version()`` — version capture and caching
- ``BootstrapComparisonEngine`` — bootstrap CI, permutation test, Cohen's d
- ``StrategyLabService`` — run creation flow with validation, analytics, comparison
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import numpy as np
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.account import Account
from app.models.asset import Asset
from app.models.catalogs import Market
from app.models.strategy import Strategy
from app.models.strategy_lab import Experiment, StrategyVersion
from app.models.trade import Trade
from app.modules.analytics.schemas import AnalyticsFilter
from app.modules.analytics.service import AnalyticsService

# ======================================================================
# get_engine_version tests
# ======================================================================


class TestGetEngineVersion:
    """Verify version capture strategy and caching."""

    def test_returns_string(self):
        """get_engine_version() returns a non-empty string."""
        from app.modules.strategy_lab._version import get_engine_version

        version = get_engine_version()
        assert isinstance(version, str)
        assert len(version) > 0

    def test_cached_return(self):
        """Repeated calls return the same value (lru_cache)."""
        from app.modules.strategy_lab._version import get_engine_version

        v1 = get_engine_version()
        v2 = get_engine_version()
        assert v1 == v2

    def test_fallback_git_version(self):
        """When importlib.metadata fails, falls back to git describe."""
        from app.modules.strategy_lab._version import get_engine_version

        # Clear the cache to force re-evaluation
        get_engine_version.cache_clear()

        with patch(
            "importlib.metadata.version",
            side_effect=Exception("no package"),
        ):
            version = get_engine_version()
            # In the test env, git describe should work
            assert isinstance(version, str)
            assert len(version) > 0

    def test_raises_on_total_failure(self):
        """RuntimeError when both methods fail."""
        from app.modules.strategy_lab._version import get_engine_version

        get_engine_version.cache_clear()

        import app.modules.strategy_lab._version as _ver_mod

        with patch(
            "importlib.metadata.version",
            side_effect=Exception("no package"),
        ):
            with patch.object(
                _ver_mod.subprocess,
                "run",
                side_effect=FileNotFoundError("no git"),
            ):
                with pytest.raises(RuntimeError, match="Cannot determine"):
                    get_engine_version()


# ======================================================================
# BootstrapComparisonEngine tests
# ======================================================================


class TestBootstrapComparisonEngine:
    """Statistical correctness of bootstrap comparison."""

    @pytest.fixture
    def engine(self):
        from app.modules.strategy_lab.implementations.bootstrap_comparison_engine import (
            BootstrapComparisonEngine,
        )

        return BootstrapComparisonEngine()

    def test_identical_groups(self, engine):
        """Identical groups → p-value ~1.0, confidence 'insufficient'."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        result = engine.compare("test_metric", values, values, seed=42)
        assert result.p_value > 0.9
        assert result.confidence == "insufficient"
        assert result.diff_mean == 0.0
        assert result.effect_size == 0.0

    def test_different_groups(self, engine):
        """Clearly different groups → p-value < 0.05, medium or higher confidence."""
        group_a = [1.0, 2.0, 1.5, 2.5, 2.0, 1.8, 2.2, 1.2, 1.7, 2.3]
        group_b = [8.0, 9.0, 8.5, 9.5, 9.0, 8.8, 9.2, 8.2, 8.7, 9.3]
        result = engine.compare("test_metric", group_a, group_b, seed=42)
        assert result.p_value < 0.05
        assert result.confidence in ("medium", "high")
        assert result.diff_mean < -5.0  # A is much smaller than B

    def test_deterministic_seed(self, engine):
        """Same seed produces identical results."""
        a = [1.0, 2.0, 3.0, 4.0, 5.0]
        b = [6.0, 7.0, 8.0, 9.0, 10.0]
        r1 = engine.compare("m", a, b, seed=123)
        r2 = engine.compare("m", a, b, seed=123)
        assert r1.p_value == r2.p_value
        assert r1.ci_lower == r2.ci_lower
        assert r1.ci_upper == r2.ci_upper
        assert r1.diff_mean == r2.diff_mean

    def test_ci_contains_true_diff(self, engine):
        """Bootstrap CI contains the true population difference."""
        rng = np.random.default_rng(42)
        # Generate two groups with known means
        a = list(rng.normal(loc=10.0, scale=1.0, size=100))
        b = list(rng.normal(loc=12.0, scale=1.0, size=100))
        true_diff = float(np.mean(a) - np.mean(b))
        result = engine.compare("m", a, b, seed=99)
        assert result.ci_lower <= true_diff <= result.ci_upper

    def test_compare_multiple(self, engine):
        """compare_multiple handles multiple metrics."""
        metrics = {
            "metric_a": ([1.0, 2.0, 3.0], [4.0, 5.0, 6.0]),
            "metric_b": ([10.0, 11.0, 12.0], [13.0, 14.0, 15.0]),
        }
        results = engine.compare_multiple(metrics, seed=42)
        assert len(results) == 2
        assert results[0].metric_name == "metric_a"
        assert results[1].metric_name == "metric_b"

    def test_small_samples(self, engine):
        """Engine handles very small samples without crashing."""
        a = [1.0]
        b = [2.0]
        result = engine.compare("small", a, b, seed=42, n_resamples=100)
        assert isinstance(result.p_value, float)
        assert result.n_trials == 100

    def test_empty_group_a(self, engine):
        """Engine produces NaN/inf for empty input (numpy semantics)."""
        import math

        result = engine.compare("empty", [], [1.0, 2.0], seed=42)
        assert math.isnan(result.run_a_value) or result.run_a_value == 0.0

    def test_cohens_d_zero_for_identical(self, engine):
        """Cohen's d is 0.0 for identical groups."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        result = engine.compare("d", values, values, seed=42)
        assert result.effect_size == 0.0

    def test_large_effect_size(self, engine):
        """Large group differences produce large Cohen's d."""
        a = [1.0, 1.5, 0.8, 1.2, 1.1] * 4
        b = [100.0, 101.0, 99.0, 100.5, 99.5] * 4
        result = engine.compare("large_d", a, b, seed=42)
        assert abs(result.effect_size) > 5.0


# ======================================================================
# StrategyLabService tests
# ======================================================================


@pytest.fixture
async def market(uow):
    """Create a Market for the test."""
    m = Market(name="Forex")
    await uow.markets.add(m)
    return m


@pytest.fixture
async def account(uow):
    """Create an Account for the test."""
    acc = Account(name="test_account")
    await uow.accounts.add(acc)
    return acc


@pytest.fixture
async def asset(uow, market):
    """Create an Asset for the test."""
    a = Asset(market_id=market.id, symbol="EURUSD", name="Euro/USD")
    await uow.assets.add(a)
    return a


@pytest.fixture
async def strategy(uow):
    """Create a Strategy for the test."""
    s = Strategy(name="test_strategy")
    await uow.strategies.add(s)
    return s


@pytest.fixture
async def strategy_version(uow, strategy):
    """Create a StrategyVersion for the test."""
    sv = StrategyVersion(strategy_id=strategy.id, version=1, parameters={"param_a": 0.5})
    await uow.strategy_versions.add(sv)
    return sv


@pytest.fixture
async def experiment(uow):
    """Create an Experiment for the test."""
    exp = Experiment(name="test_experiment", description="Test experiment")
    await uow.experiments.add(exp)
    return exp


async def _create_closed_trade(uow, account, asset, direction, entry, exit, qty=1.0):
    """Helper to create a closed trade with PnL data."""
    trade = Trade(
        account_id=account.id,
        asset_id=asset.id,
        direction=direction,
        status="closed",
        entry_price=entry,
        exit_price=exit,
        quantity=qty,
        entry_datetime="2026-01-01T00:00:00",
        exit_datetime="2026-01-02T00:00:00",
        commission=0.0,
    )
    await uow.trades.add(trade)
    return trade


@pytest.fixture
async def closed_trades(uow, account, asset):
    """Create a set of closed trades for testing."""
    trades = []
    # Pre-sorted PnL sets — group A (profitable) and group B (unprofitable)
    for i in range(3):
        t = await _create_closed_trade(
            uow, account, asset, "long", entry=100.0 + i, exit=110.0 + i, qty=1.0
        )
        trades.append(t)
    return trades


@pytest.fixture
async def losing_trades(uow, account, asset):
    """Create losing trades (Feb dates) for baseline run comparison."""
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
            entry_datetime="2026-02-10T00:00:00",
            exit_datetime="2026-02-15T00:00:00",
            commission=0.0,
        )
        await uow.trades.add(trade)
        trades.append(trade)
    return trades


@pytest.fixture
def analytics_service(uow):
    """Create an AnalyticsService with the test UoW."""
    return AnalyticsService(uow)


@pytest.fixture
def comparison_engine():
    """Create a BootstrapComparisonEngine for tests."""
    from app.modules.strategy_lab.implementations.bootstrap_comparison_engine import (
        BootstrapComparisonEngine,
    )

    return BootstrapComparisonEngine()


@pytest.fixture
def lab_service(uow, analytics_service, comparison_engine):
    """Create the StrategyLabService under test."""
    from app.modules.strategy_lab.service import StrategyLabService

    return StrategyLabService(
        uow=uow,
        analytics_service=analytics_service,
        comparison_engine=comparison_engine,
    )


class TestCreateRun:
    """Verify the 9-step create_run flow."""

    @pytest.mark.asyncio
    async def test_create_run_success(
        self, lab_service, experiment, strategy_version, closed_trades
    ):
        """Successful run creates Run record with status='completed'."""
        filters = AnalyticsFilter(
            date_from=datetime(2026, 1, 1),
            date_to=datetime(2026, 1, 31),
        )
        run = await lab_service.create_run(
            experiment_id=experiment.id,
            strategy_version_id=strategy_version.id,
            filters=filters,
        )

        assert run.id is not None
        assert run.status == "completed"
        assert run.engine_version is not None
        assert len(run.engine_version) > 0
        assert run.dataset_snapshot_id is not None
        assert run.experiment_id == experiment.id
        assert run.strategy_version_id == strategy_version.id
        assert run.baseline_run_id is None
        assert run.error_message is None

    @pytest.mark.asyncio
    async def test_create_run_fails_without_engine_version(
        self, lab_service, experiment, strategy_version
    ):
        """Run creation fails when engine version can't be captured."""
        import app.modules.strategy_lab.service as svc_mod

        with patch.object(
            svc_mod,
            "get_engine_version",
            side_effect=RuntimeError("Cannot determine"),
        ):
            with pytest.raises(RuntimeError, match="Cannot determine"):
                await lab_service.create_run(
                    experiment_id=experiment.id,
                    strategy_version_id=strategy_version.id,
                    filters=AnalyticsFilter(),
                )

    @pytest.mark.asyncio
    async def test_create_run_missing_strategy_version(
        self, lab_service, experiment, closed_trades
    ):
        """Run creation fails with NotFoundError when StrategyVersion doesn't exist."""
        from app.core.exceptions import NotFoundError

        with pytest.raises(NotFoundError, match="not found"):
            await lab_service.create_run(
                experiment_id=experiment.id,
                strategy_version_id=99999,
                filters=AnalyticsFilter(),
            )

    @pytest.mark.asyncio
    async def test_create_run_duplicate(
        self, lab_service, experiment, strategy_version, closed_trades
    ):
        """Duplicate run config raises IntegrityError."""
        filters = AnalyticsFilter(
            date_from=datetime(2026, 1, 1),
            date_to=datetime(2026, 1, 31),
        )

        # First run succeeds
        await lab_service.create_run(
            experiment_id=experiment.id,
            strategy_version_id=strategy_version.id,
            filters=filters,
        )

        # Second run with same config should fail
        with pytest.raises(IntegrityError):
            await lab_service.create_run(
                experiment_id=experiment.id,
                strategy_version_id=strategy_version.id,
                filters=filters,
            )

    @pytest.mark.asyncio
    async def test_create_run_with_comparison(
        self,
        lab_service,
        uow,
        experiment,
        strategy_version,
        closed_trades,
        losing_trades,
    ):
        """Comparison run stores RunMetric with comparison results."""
        # Baseline run with losing trades
        baseline_filters = AnalyticsFilter(
            date_from=datetime(2026, 1, 1),
            date_to=datetime(2026, 2, 1),
        )
        baseline_run = await lab_service.create_run(
            experiment_id=experiment.id,
            strategy_version_id=strategy_version.id,
            filters=baseline_filters,
        )

        # Second run with winning trades, referencing baseline
        comparison_filters = AnalyticsFilter(
            date_from=datetime(2026, 2, 1),
            date_to=datetime(2026, 3, 1),
        )
        comparison_run = await lab_service.create_run(
            experiment_id=experiment.id,
            strategy_version_id=strategy_version.id,
            filters=comparison_filters,
            baseline_run_id=baseline_run.id,
        )

        # Verify RunMetric was created
        metrics, _ = await uow.run_metrics.list(run_id=comparison_run.id)
        assert len(metrics) == 1
        metric = metrics[0]
        assert metric.metric_name == "net_pnl"
        assert metric.ci_lower is not None
        assert metric.ci_upper is not None
        assert metric.p_value is not None
        assert metric.effect_size is not None


# ======================================================================
# Integration: Engine + Service interaction
# ======================================================================


class TestServiceIntegration:
    """Verify end-to-end service flows."""

    @pytest.mark.asyncio
    async def test_full_experiment_workflow(
        self,
        lab_service,
        uow,
        experiment,
        strategy,
        strategy_version,
        closed_trades,
    ):
        """Full workflow: create experiment → strategy version → run."""
        # Experiment already created by fixture
        assert experiment.id is not None

        # Create a second strategy version
        sv2 = await lab_service.create_strategy_version(
            strategy_id=strategy.id,
            parameters={"param_b": 0.8},
            change_log="Tweaked parameter",
        )
        assert sv2.version == 2  # auto-incremented
        assert sv2.parameters == {"param_b": 0.8}

        # Create run with the new version
        filters = AnalyticsFilter(
            date_from=datetime(2026, 1, 1),
            date_to=datetime(2026, 1, 31),
        )
        run = await lab_service.create_run(
            experiment_id=experiment.id,
            strategy_version_id=sv2.id,
            filters=filters,
        )
        assert run.status == "completed"
        assert run.strategy_version_id == sv2.id

    @pytest.mark.asyncio
    async def test_create_experiment(self, lab_service, uow):
        """create_experiment creates an experiment with draft status."""
        exp = await lab_service.create_experiment(
            name="new_exp",
            description="A test experiment",
            hypothesis="Strategy X outperforms",
        )
        assert exp.id is not None
        assert exp.name == "new_exp"
        assert exp.description == "A test experiment"
        assert exp.hypothesis == "Strategy X outperforms"
        assert exp.status == "draft"
