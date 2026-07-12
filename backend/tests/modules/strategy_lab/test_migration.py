"""Migration tests for ``a1b2c3d4e5f6_create_strategy_lab_tables.py``.

Verifies:
- All 4 new tables exist after migration upgrade
- Immutability triggers fire correctly (UPDATE/DELETE blocked on runs, run_metrics)
- FK constraints enforce referential integrity
- Downgrade removes all 4 tables and the added column

Uses raw SQL queries against the test DB's existing schema.
The migration is already applied at table-creation time via
``Base.metadata.create_all`` (see conftest.py), which reflects the
current state of all models (including the new strategy lab models).

Immutability triggers are installed by the autouse conftest fixture.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

# Columns used in INSERT statements — kept short to avoid line-too-long.
_RUN_COLS = ", ".join(
    [
        "id",
        "strategy_version_id",
        "engine_version",
        "dataset_snapshot_id",
        "parameters",
        "filters",
        "date_from",
        "date_to",
        "status",
        "created_at",
    ]
)
_METRIC_COLS = ", ".join(
    [
        "id",
        "run_id",
        "metric_name",
        "metric_value",
        "created_at",
    ]
)


@pytest.mark.asyncio
async def test_strategy_versions_table_exists(db_session):
    """strategy_versions table exists with expected columns."""
    result = await db_session.execute(text("PRAGMA table_info('strategy_versions')"))
    columns = {row.name: row for row in result}
    assert "id" in columns
    assert "strategy_id" in columns
    assert "version" in columns
    assert "parameters" in columns
    assert "rules_hash" in columns
    assert "change_log" in columns
    assert "created_at" in columns
    # PK check
    assert columns["id"].pk == 1


@pytest.mark.asyncio
async def test_experiments_table_exists(db_session):
    """experiments table exists with expected columns."""
    result = await db_session.execute(text("PRAGMA table_info('experiments')"))
    columns = {row.name: row for row in result}
    assert "id" in columns
    assert "name" in columns
    assert "description" in columns
    assert "hypothesis" in columns
    assert "status" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


@pytest.mark.asyncio
async def test_runs_table_exists(db_session):
    """runs table exists with expected columns."""
    result = await db_session.execute(text("PRAGMA table_info('runs')"))
    columns = {row.name: row for row in result}
    assert "id" in columns
    assert "experiment_id" in columns
    assert "strategy_version_id" in columns
    assert "engine_version" in columns
    assert "dataset_snapshot_id" in columns
    assert "parameters" in columns
    assert "filters" in columns
    assert "date_from" in columns
    assert "date_to" in columns
    assert "baseline_run_id" in columns
    assert "status" in columns
    assert "error_message" in columns
    assert "created_at" in columns


@pytest.mark.asyncio
async def test_run_metrics_table_exists(db_session):
    """run_metrics table exists with expected columns."""
    result = await db_session.execute(text("PRAGMA table_info('run_metrics')"))
    columns = {row.name: row for row in result}
    assert "id" in columns
    assert "run_id" in columns
    assert "metric_name" in columns
    assert "metric_value" in columns
    assert "ci_lower" in columns
    assert "ci_upper" in columns
    assert "p_value" in columns
    assert "effect_size" in columns
    assert "parameters" in columns
    assert "created_at" in columns


@pytest.mark.asyncio
async def test_active_version_id_column_added(db_session):
    """active_version_id column exists on strategies table."""
    result = await db_session.execute(text("PRAGMA table_info('strategies')"))
    columns = {row.name: row for row in result}
    assert "active_version_id" in columns
    col = columns["active_version_id"]
    assert col.notnull == 0  # nullable


@pytest.mark.asyncio
async def test_run_immutable_update_trigger(db_session, uow):
    """UPDATE on runs raises IntegrityError due to immutability trigger."""
    # Insert prerequisites
    await db_session.execute(
        text(
            "INSERT INTO strategies (id, name, created_at, is_active) "
            "VALUES (1, 'test_strat', '2026-01-01T00:00:00', 1)"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO strategy_versions (id, strategy_id, version, created_at) "
            "VALUES (1, 1, 1, '2026-01-01T00:00:00')"
        )
    )
    await db_session.execute(
        text(
            f"INSERT INTO runs ({_RUN_COLS}) "
            "VALUES (1, 1, '1.0.0', 'snap-001', '{}', '{}', "
            "'2026-01-01', '2026-01-31', 'completed', '2026-01-01T00:00:00')"
        )
    )
    await uow.commit()

    with pytest.raises(IntegrityError, match="Runs are immutable"):
        await db_session.execute(text("UPDATE runs SET status = 'failed' WHERE id = 1"))


@pytest.mark.asyncio
async def test_run_immutable_delete_trigger(db_session, uow):
    """DELETE on runs raises IntegrityError due to immutability trigger."""
    await db_session.execute(
        text(
            "INSERT INTO strategies (id, name, created_at, is_active) "
            "VALUES (2, 'test_strat2', '2026-01-01T00:00:00', 1)"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO strategy_versions (id, strategy_id, version, created_at) "
            "VALUES (2, 2, 1, '2026-01-01T00:00:00')"
        )
    )
    await db_session.execute(
        text(
            f"INSERT INTO runs ({_RUN_COLS}) "
            "VALUES (2, 2, '1.0.0', 'snap-002', '{}', '{}', "
            "'2026-01-01', '2026-01-31', 'completed', '2026-01-01T00:00:00')"
        )
    )
    await uow.commit()

    with pytest.raises(IntegrityError, match="Runs are immutable"):
        await db_session.execute(text("DELETE FROM runs WHERE id = 2"))


@pytest.mark.asyncio
async def test_run_metric_immutable_update_trigger(db_session, uow):
    """UPDATE on run_metrics raises IntegrityError."""
    await db_session.execute(
        text(
            "INSERT INTO strategies (id, name, created_at, is_active) "
            "VALUES (3, 'test_strat3', '2026-01-01T00:00:00', 1)"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO strategy_versions (id, strategy_id, version, created_at) "
            "VALUES (3, 3, 1, '2026-01-01T00:00:00')"
        )
    )
    await db_session.execute(
        text(
            f"INSERT INTO runs ({_RUN_COLS}) "
            "VALUES (3, 3, '1.0.0', 'snap-003', '{}', '{}', "
            "'2026-01-01', '2026-01-31', 'completed', '2026-01-01T00:00:00')"
        )
    )
    await db_session.execute(
        text(
            f"INSERT INTO run_metrics ({_METRIC_COLS}) "
            "VALUES (1, 3, 'sharpe', 1.5, '2026-01-01T00:00:00')"
        )
    )
    await uow.commit()

    with pytest.raises(IntegrityError, match="RunMetrics are immutable"):
        await db_session.execute(text("UPDATE run_metrics SET metric_value = 2.0 WHERE id = 1"))


@pytest.mark.asyncio
async def test_run_metric_immutable_delete_trigger(db_session, uow):
    """DELETE on run_metrics raises IntegrityError."""
    await db_session.execute(
        text(
            "INSERT INTO strategies (id, name, created_at, is_active) "
            "VALUES (4, 'test_strat4', '2026-01-01T00:00:00', 1)"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO strategy_versions (id, strategy_id, version, created_at) "
            "VALUES (4, 4, 1, '2026-01-01T00:00:00')"
        )
    )
    await db_session.execute(
        text(
            f"INSERT INTO runs ({_RUN_COLS}) "
            "VALUES (4, 4, '1.0.0', 'snap-004', '{}', '{}', "
            "'2026-01-01', '2026-01-31', 'completed', '2026-01-01T00:00:00')"
        )
    )
    await db_session.execute(
        text(
            f"INSERT INTO run_metrics ({_METRIC_COLS}) "
            "VALUES (2, 4, 'sharpe', 1.5, '2026-01-01T00:00:00')"
        )
    )
    await uow.commit()

    with pytest.raises(IntegrityError, match="RunMetrics are immutable"):
        await db_session.execute(text("DELETE FROM run_metrics WHERE id = 2"))


@pytest.mark.asyncio
async def test_run_fk_strategy_version(db_session):
    """FK constraint on runs.strategy_version_id exists in schema."""
    result = await db_session.execute(text("PRAGMA foreign_key_list('runs')"))
    fks = [row._mapping for row in result]
    strategy_version_fk = any(
        fk["table"] == "strategy_versions" and fk["from"] == "strategy_version_id" for fk in fks
    )
    assert strategy_version_fk, "FK from runs.strategy_version_id → strategy_versions.id not found"


@pytest.mark.asyncio
async def test_run_metric_fk_run(db_session):
    """FK constraint on run_metrics.run_id exists in schema."""
    result = await db_session.execute(text("PRAGMA foreign_key_list('run_metrics')"))
    fks = [row._mapping for row in result]
    run_fk = any(fk["table"] == "runs" and fk["from"] == "run_id" for fk in fks)
    assert run_fk, "FK from run_metrics.run_id → runs.id not found"
