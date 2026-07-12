"""create strategy lab tables — strategy_versions, experiments, runs, run_metrics

Revision ID: a1b2c3d4e5f6
Revises: ebc4b9c1a9a0
Create Date: 2026-07-12 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "ebc4b9c1a9a0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Create strategy_versions ──────────────────────────────────────────
    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("rules_hash", sa.Text(), nullable=True),
        sa.Column("setup_ids", sa.JSON(), nullable=True),
        sa.Column("change_log", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["strategy_id"],
            ["strategies.id"],
            name=op.f("fk_strategy_versions_strategy_id_strategies"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_strategy_versions")),
        sa.UniqueConstraint(
            "strategy_id", "version", name="uq_strategy_version"
        ),
    )
    op.create_index(
        op.f("ix_strategy_versions_strategy_id"),
        "strategy_versions",
        ["strategy_id"],
        unique=False,
    )

    # ── Create experiments ────────────────────────────────────────────────
    op.create_table(
        "experiments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_experiments")),
    )

    # ── Create runs ───────────────────────────────────────────────────────
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=True),
        sa.Column("strategy_version_id", sa.Integer(), nullable=False),
        sa.Column("engine_version", sa.Text(), nullable=False),
        sa.Column("dataset_snapshot_id", sa.Text(), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("baseline_run_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["experiment_id"],
            ["experiments.id"],
            name=op.f("fk_runs_experiment_id_experiments"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_version_id"],
            ["strategy_versions.id"],
            name=op.f("fk_runs_strategy_version_id_strategy_versions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_run_id"],
            ["runs.id"],
            name=op.f("fk_runs_baseline_run_id_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_runs")),
        sa.UniqueConstraint(
            "strategy_version_id", "parameters", "filters",
            "date_from", "date_to", "engine_version",
            name="uq_run_identity",
        ),
    )
    op.create_index(
        op.f("ix_runs_experiment_id"),
        "runs",
        ["experiment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runs_strategy_version_id"),
        "runs",
        ["strategy_version_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_runs_baseline_run_id"),
        "runs",
        ["baseline_run_id"],
        unique=False,
    )

    # ── Create run_metrics ────────────────────────────────────────────────
    op.create_table(
        "run_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("ci_lower", sa.Float(), nullable=True),
        sa.Column("ci_upper", sa.Float(), nullable=True),
        sa.Column("p_value", sa.Float(), nullable=True),
        sa.Column("effect_size", sa.Float(), nullable=True),
        sa.Column("parameters", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["runs.id"],
            name=op.f("fk_run_metrics_run_id_runs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_run_metrics")),
    )
    op.create_index(
        op.f("ix_run_metrics_run_id"),
        "run_metrics",
        ["run_id"],
        unique=False,
    )

    # ── Add active_version_id to strategies ──────────────────────────────
    with op.batch_alter_table("strategies") as batch_op:
        batch_op.add_column(
            sa.Column("active_version_id", sa.Integer(), nullable=True),
        )
        batch_op.create_foreign_key(
            op.f("fk_strategies_active_version_id_strategy_versions"),
            "strategy_versions",
            ["active_version_id"],
            ["id"],
        )

    # ── Immutability triggers ────────────────────────────────────────────
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_run_immutable_update
        BEFORE UPDATE ON runs
        BEGIN
            SELECT RAISE(ABORT, 'Runs are immutable - cannot UPDATE');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_run_immutable_delete
        BEFORE DELETE ON runs
        BEGIN
            SELECT RAISE(ABORT, 'Runs are immutable - cannot DELETE');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_run_metric_immutable_update
        BEFORE UPDATE ON run_metrics
        BEGIN
            SELECT RAISE(ABORT, 'RunMetrics are immutable - cannot UPDATE');
        END;
        """
    )
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_run_metric_immutable_delete
        BEFORE DELETE ON run_metrics
        BEGIN
            SELECT RAISE(ABORT, 'RunMetrics are immutable - cannot DELETE');
        END;
        """
    )


def downgrade() -> None:
    # ── Drop immutability triggers ────────────────────────────────────────
    op.execute("DROP TRIGGER IF EXISTS trg_run_immutable_update")
    op.execute("DROP TRIGGER IF EXISTS trg_run_immutable_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_run_metric_immutable_update")
    op.execute("DROP TRIGGER IF EXISTS trg_run_metric_immutable_delete")

    # ── Drop active_version_id from strategies ────────────────────────────
    with op.batch_alter_table("strategies") as batch_op:
        batch_op.drop_constraint(
            op.f("fk_strategies_active_version_id_strategy_versions"),
            type_="foreignkey",
        )
        batch_op.drop_column("active_version_id")

    # ── Drop tables ───────────────────────────────────────────────────────
    op.drop_table("run_metrics")
    op.drop_table("runs")
    op.drop_table("experiments")
    op.drop_table("strategy_versions")
