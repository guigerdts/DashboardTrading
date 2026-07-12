"""Strategy Lab domain models — experiments, runs, metrics, and versioning.

All models use SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.

Key design decisions:
- Runs are IMMUTABLE after creation (DB-level triggers enforce this).
- RunMetrics are IMMUTABLE after creation (same DB-level trigger pattern).
- ``StrategyVersion`` version numbers auto-increment per ``strategy_id``.
- ``Run`` identity uniqueness is enforced by a composite UniqueConstraint.
"""

from __future__ import annotations

from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy import JSON, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class StrategyVersion(Base):
    """A versioned snapshot of a strategy's parameters and rules.

    Each ``strategy_id`` has its own auto-incrementing ``version`` sequence.
    This enables full reproducibility — every Run references exactly one
    StrategyVersion with the parameters it used.

    References
    ----------
    - BR-SL-01: ``version`` auto-increments per ``strategy_id``
    - BR-SL-02: ``rules_hash`` SHA-256 of the combined rules
    """

    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rules_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    setup_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    change_log: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=sa.func.now(),
    )

    __table_args__ = (sa.UniqueConstraint("strategy_id", "version", name="uq_strategy_version"),)


class Experiment(Base):
    """A named experiment that groups related Runs.

    Experiments track research hypotheses and their outcomes.
    Status transitions: draft → running → completed | aborted
    """

    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="draft",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class Run(Base):
    """A single backtest execution — IMMUTABLE after creation.

    Stores ALL parameters needed for exact reproducibility, including
    engine version, dataset snapshot, parameters, filters, and date range.

    References
    ----------
    - BR-SL-03: Runs are immutable — DB triggers block UPDATE/DELETE
    - BR-SL-04: Identity uniqueness via ``uq_run_identity``
    """

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    experiment_id: Mapped[int | None] = mapped_column(
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
    )
    strategy_version_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Reproducibility (ALL mandatory) ──────────────────────────────
    engine_version: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_snapshot_id: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    filters: Mapped[dict] = mapped_column(JSON, nullable=False)
    date_from: Mapped[date] = mapped_column(sa.Date, nullable=False)
    date_to: Mapped[date] = mapped_column(sa.Date, nullable=False)

    # ── Comparison ───────────────────────────────────────────────────
    baseline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Execution ────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="running",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=sa.func.now(),
    )

    # ── Relationships ────────────────────────────────────────────────
    strategy_version: Mapped[StrategyVersion] = relationship("StrategyVersion", lazy="raise")
    experiment: Mapped[Experiment | None] = relationship("Experiment", lazy="raise")

    __table_args__ = (
        sa.UniqueConstraint(
            "strategy_version_id",
            "parameters",
            "filters",
            "date_from",
            "date_to",
            "engine_version",
            name="uq_run_identity",
        ),
    )


class RunMetric(Base):
    """A single metric computed from a Run — IMMUTABLE after creation.

    Stores one metric per row (e.g. sharpe_ratio, total_return, max_drawdown)
    with optional confidence intervals and statistical significance.

    References
    ----------
    - BR-SL-05: RunMetrics are immutable — DB triggers block UPDATE/DELETE
    """

    __tablename__ = "run_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    ci_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    effect_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime,
        nullable=False,
        server_default=sa.func.now(),
    )

    # ── Relationships ────────────────────────────────────────────────
    run: Mapped[Run] = relationship("Run", lazy="raise")
