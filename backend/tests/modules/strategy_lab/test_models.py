"""Model tests for Strategy Lab entities.

Covers:
- StrategyVersion creation and auto-increment per strategy_id
- Experiment status transitions
- Run identity uniqueness constraint
- RunMetric relationship with Run
"""

from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.strategy import Strategy
from app.models.strategy_lab import Experiment, Run, RunMetric, StrategyVersion


@pytest.mark.asyncio
async def test_strategy_version_auto_increment(uow):
    """StrategyVersion version auto-increments per strategy_id."""
    # Prerequisite: strategy record
    strat = Strategy(name="sv_test")
    await uow.strategies.add(strat)

    sv1 = StrategyVersion(strategy_id=strat.id, version=1)
    await uow.strategy_versions.add(sv1)
    assert sv1.id is not None

    # Second version for same strategy
    sv2 = StrategyVersion(strategy_id=strat.id, version=2)
    await uow.strategy_versions.add(sv2)
    assert sv2.id is not None
    assert sv2.version == 2

    # Different strategy can have version 1 too
    strat2 = Strategy(name="sv_test2")
    await uow.strategies.add(strat2)
    sv3 = StrategyVersion(strategy_id=strat2.id, version=1)
    await uow.strategy_versions.add(sv3)
    assert sv3.id is not None
    assert sv3.version == 1


@pytest.mark.asyncio
async def test_strategy_version_duplicate_version_fails(uow):
    """Duplicate (strategy_id, version) raises IntegrityError."""
    strat = Strategy(name="dup_test")
    await uow.strategies.add(strat)

    sv1 = StrategyVersion(strategy_id=strat.id, version=1)
    await uow.strategy_versions.add(sv1)
    await uow.commit()

    sv2 = StrategyVersion(strategy_id=strat.id, version=1)
    with pytest.raises(IntegrityError):
        await uow.strategy_versions.add(sv2)
        await uow.commit()


@pytest.mark.asyncio
async def test_experiment_creates_with_draft_status(uow):
    """Experiment defaults to 'draft' status."""
    exp = Experiment(name="test_experiment")
    await uow.experiments.add(exp)
    assert exp.status == "draft"


@pytest.mark.asyncio
async def _create_run_prereqs(uow, strat_name="prereq_strat"):
    """Create prerequisite Strategy + StrategyVersion for Run tests."""
    strat = Strategy(name=strat_name)
    await uow.strategies.add(strat)
    sv = StrategyVersion(strategy_id=strat.id, version=1)
    await uow.strategy_versions.add(sv)
    return sv


@pytest.mark.asyncio
async def test_run_identity_uniqueness(uow):
    """Duplicate run identity raises IntegrityError."""
    sv = await _create_run_prereqs(uow)

    run1 = Run(
        strategy_version_id=sv.id,
        engine_version="1.0.0",
        dataset_snapshot_id="snap-001",
        parameters={},
        filters={},
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )
    await uow.runs.add(run1)
    await uow.commit()

    run2 = Run(
        strategy_version_id=sv.id,
        engine_version="1.0.0",
        dataset_snapshot_id="snap-001",
        parameters={},
        filters={},
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )
    with pytest.raises(IntegrityError):
        await uow.runs.add(run2)
        await uow.commit()


@pytest.mark.asyncio
async def test_different_run_identity_allowed(uow):
    """Changing any identity field (e.g. date_to) allows a new Run."""
    sv = await _create_run_prereqs(uow)

    run1 = Run(
        strategy_version_id=sv.id,
        engine_version="1.0.0",
        dataset_snapshot_id="snap-001",
        parameters={},
        filters={},
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )
    await uow.runs.add(run1)
    await uow.commit()

    # Different date_to
    run2 = Run(
        strategy_version_id=sv.id,
        engine_version="1.0.0",
        dataset_snapshot_id="snap-001",
        parameters={},
        filters={},
        date_from=date(2026, 1, 1),
        date_to=date(2026, 2, 1),
    )
    await uow.runs.add(run2)
    await uow.commit()
    assert run2.id != run1.id


@pytest.mark.asyncio
async def test_run_metric_relationship(uow):
    """RunMetric can be associated with a Run and read back."""
    sv = await _create_run_prereqs(uow)

    run = Run(
        strategy_version_id=sv.id,
        engine_version="1.0.0",
        dataset_snapshot_id="snap-001",
        parameters={},
        filters={},
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )
    await uow.runs.add(run)

    metric = RunMetric(
        run_id=run.id,
        metric_name="sharpe_ratio",
        metric_value=1.5,
        ci_lower=1.0,
        ci_upper=2.0,
    )
    await uow.run_metrics.add(metric)
    await uow.commit()

    assert metric.run_id == run.id
    assert metric.metric_name == "sharpe_ratio"
    assert metric.metric_value == 1.5


@pytest.mark.asyncio
async def test_experiment_status_transitions(uow):
    """Experiment status can transition between valid values."""
    exp = Experiment(name="transition_test", description="Testing transitions")
    await uow.experiments.add(exp)
    assert exp.status == "draft"

    exp.status = "running"
    await uow.experiments.update(exp)
    await uow.commit()
    assert exp.status == "running"

    # Refresh and verify
    fetched = await uow.experiments.get(exp.id)
    assert fetched is not None
    assert fetched.status == "running"


@pytest.mark.asyncio
async def test_run_immutable_repository(uow):
    """RunRepository raises NotImplementedError for update and delete."""
    sv = await _create_run_prereqs(uow)

    run = Run(
        strategy_version_id=sv.id,
        engine_version="1.0.0",
        dataset_snapshot_id="snap-001",
        parameters={},
        filters={},
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 31),
    )
    await uow.runs.add(run)
    await uow.commit()

    with pytest.raises(NotImplementedError, match="Runs are immutable"):
        await uow.runs.update(run)

    with pytest.raises(NotImplementedError, match="Runs are immutable"):
        await uow.runs.delete(run)
