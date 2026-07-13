"""StrategyLabService — orchestrates experiment creation, run execution, and comparison.

Each ``create_run`` call follows a 9-step flow that validates inputs,
resolves the dataset, checks uniqueness, calls the analytics engine,
and optionally compares against a baseline run.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Any

from app.core.exceptions import NotFoundError
from app.db.unit_of_work import UnitOfWork
from app.models.strategy_lab import Experiment, Run, RunMetric, StrategyVersion
from app.modules.analytics.calculators.pnl import compute_pnl
from app.modules.analytics.schemas import AnalyticsFilter
from app.modules.analytics.service import AnalyticsService

from ._version import get_engine_version
from .interfaces.comparison_engine import ComparisonEngine, ComparisonResult


def _serialize_filters(filters: AnalyticsFilter) -> dict[str, Any]:
    """Convert AnalyticsFilter to a JSON-safe dict.

    Converts ``datetime`` values to ISO-format strings so the dict
    can be stored in a SQLAlchemy JSON column.
    """
    raw = filters.model_dump(exclude_none=True)
    serialized: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def _filter_to_dates(
    filters: AnalyticsFilter,
) -> tuple[date, date]:
    """Extract date_from/date_to from filters with safe defaults."""
    date_from = filters.date_from.date() if filters.date_from else date(1900, 1, 1)
    date_to = filters.date_to.date() if filters.date_to else date(2099, 12, 31)
    return date_from, date_to


class StrategyLabService:
    """Orchestrator for strategy experiments, runs, and comparisons.

    Parameters
    ----------
    uow : UnitOfWork
        Shared transaction boundary.
    analytics_service : AnalyticsService
        Read-only analytics calculator (same-process call).
    comparison_engine : ComparisonEngine
        Statistical comparison engine for A/B analysis.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        analytics_service: AnalyticsService,
        comparison_engine: ComparisonEngine,
    ) -> None:
        self._uow = uow
        self._analytics = analytics_service
        self._comparison = comparison_engine

    async def get_experiment(self, experiment_id: int) -> Experiment | None:
        """Fetch an experiment by ID."""
        return await self._uow.experiments.get(experiment_id)

    async def list_experiments(self) -> list[Experiment]:
        """List all experiments."""
        items, _ = await self._uow.experiments.list()
        return items

    async def delete_experiment(self, experiment_id: int) -> None:
        """Delete an experiment by ID."""
        exp = await self._uow.experiments.get(experiment_id)
        if exp is None:
            raise NotFoundError(f"Experiment {experiment_id} not found")
        await self._uow.experiments.delete(exp)

    async def get_strategy_version(self, version_id: int) -> StrategyVersion | None:
        """Fetch a strategy version by ID."""
        return await self._uow.strategy_versions.get(version_id)

    async def list_strategy_versions(self, strategy_id: int) -> list[StrategyVersion]:
        """List all versions for a strategy."""
        items, _ = await self._uow.strategy_versions.list(strategy_id=strategy_id)
        return items

    async def get_run(self, run_id: int) -> Run | None:
        """Fetch a run by ID."""
        return await self._uow.runs.get(run_id)

    async def list_runs(self) -> list[Run]:
        """List all runs."""
        items, _ = await self._uow.runs.list()
        return items

    async def get_run_metrics(self, run_id: int) -> list[RunMetric]:
        """Fetch metrics for a run."""
        items, _ = await self._uow.run_metrics.list(run_id=run_id)
        return items

    async def count_runs_for_experiment(self, experiment_id: int) -> int:
        """Count how many runs reference an experiment."""
        from sqlalchemy import func, select

        from app.models.strategy_lab import Run

        query = select(func.count()).select_from(Run).where(Run.experiment_id == experiment_id)
        result = await self._uow._session.execute(query)
        return result.scalar_one()

    async def create_experiment(
        self,
        name: str,
        description: str | None = None,
        hypothesis: str | None = None,
    ) -> Experiment:
        """Create a new experiment in draft status."""
        exp = Experiment(name=name, description=description, hypothesis=hypothesis)
        return await self._uow.experiments.add(exp)

    async def create_strategy_version(
        self,
        strategy_id: int,
        parameters: dict | None = None,
        change_log: str | None = None,
    ) -> StrategyVersion:
        """Create a new version for a strategy (auto-incrementing version)."""
        _, total = await self._uow.strategy_versions.list(strategy_id=strategy_id)
        next_version = total + 1
        sv = StrategyVersion(
            strategy_id=strategy_id,
            version=next_version,
            parameters=parameters,
            change_log=change_log,
        )
        return await self._uow.strategy_versions.add(sv)

    async def create_run(
        self,
        experiment_id: int | None,
        strategy_version_id: int,
        filters: AnalyticsFilter,
        baseline_run_id: int | None = None,
    ) -> Run:
        """Execute a full 9-step run creation flow.

        Runs are DB-immutable (triggers block UPDATE/DELETE), so the
        final status is set at creation time after all processing.

        Steps
        -----
        1. Validate strategy_version exists
        2. Capture engine version (MANDATORY — fails if RuntimeError)
        3. Resolve dataset snapshot (trade IDs matching filters)
        4. Resolve date range from filters
        5. Execute analytics + optional comparison
        6. Create Run with final status + optional RunMetrics
        """
        # ── Step 1: Validate strategy_version ────────────────────────
        sv = await self._uow.strategy_versions.get(strategy_version_id)
        if sv is None:
            raise NotFoundError(f"StrategyVersion {strategy_version_id} not found")

        # ── Step 2: Capture engine version ──────────────────────────
        engine_version = get_engine_version()

        # ── Step 3: Resolve dataset snapshot ────────────────────────
        filter_kwargs = filters.to_filter_kwargs()
        trades = await self._uow.trades.list_closed(**filter_kwargs)
        trade_ids = [t.id for t in trades] if trades else []
        dataset_snapshot_id = hashlib.sha256(
            ",".join(str(tid) for tid in sorted(trade_ids)).encode()
        ).hexdigest()[:16]

        # ── Step 4: Resolve date range ──────────────────────────────
        run_date_from, run_date_to = _filter_to_dates(filters)

        # ── Step 5: Analytics + optional comparison ─────────────────
        # These are read-only queries; no Run is created yet.
        metrics: list[RunMetric] = []
        run_status = "completed"

        try:
            await self._analytics.get_summary(filters)

            if baseline_run_id is not None:
                comparison_result = await self._compute_comparison(baseline_run_id, trades, filters)
                metrics.append(
                    RunMetric(
                        metric_name=comparison_result.metric_name,
                        metric_value=comparison_result.diff_mean,
                        ci_lower=comparison_result.ci_lower,
                        ci_upper=comparison_result.ci_upper,
                        p_value=comparison_result.p_value,
                        effect_size=comparison_result.effect_size,
                    )
                )
        except Exception:
            run_status = "failed"
            # Don't re-raise — the run record still gets created
            # so the user can inspect the failure.

        # ── Step 6: Create Run (immutable — set final status) ───────
        run = Run(
            experiment_id=experiment_id,
            strategy_version_id=strategy_version_id,
            engine_version=engine_version,
            dataset_snapshot_id=dataset_snapshot_id,
            parameters=sv.parameters or {},
            filters=_serialize_filters(filters),
            date_from=run_date_from,
            date_to=run_date_to,
            baseline_run_id=baseline_run_id,
            status=run_status,
            error_message=(str(run_status) if run_status == "failed" else None),
        )
        await self._uow.runs.add(run)

        # Attach metrics now that the run has an ID
        for m in metrics:
            m.run_id = run.id
            await self._uow.run_metrics.add(m)

        return run

    async def _compute_comparison(
        self,
        baseline_run_id: int,
        trades_a: list,
        filters_a: AnalyticsFilter,
    ) -> ComparisonResult:
        """Compute comparison between current run and a baseline run."""
        baseline_run = await self._uow.runs.get(baseline_run_id)
        if baseline_run is None:
            raise NotFoundError(f"Baseline Run {baseline_run_id} not found")

        # Get baseline trades using the baseline run's stored filters
        baseline_filters_dict = baseline_run.filters
        baseline_filter = AnalyticsFilter(**baseline_filters_dict)
        baseline_trades = await self._uow.trades.list_closed(**baseline_filter.to_filter_kwargs())

        # Per-trade PnL values for both groups
        values_a = [compute_pnl(t) for t in trades_a]
        values_b = [compute_pnl(t) for t in baseline_trades]

        return self._comparison.compare(
            metric_name="net_pnl",
            values_a=values_a,
            values_b=values_b,
        )

    async def get_comparison(
        self,
        run_id: int,
        baseline_run_id: int,
    ) -> ComparisonResult:
        """Compare two runs and return the comparison result.

        Loads the trades for each run from their stored filters,
        computes per-trade PnL, and delegates to the comparison engine.
        """
        run = await self._uow.runs.get(run_id)
        if run is None:
            raise NotFoundError(f"Run {run_id} not found")

        filters_dict = run.filters
        run_filter = AnalyticsFilter(**filters_dict)
        trades_a = await self._uow.trades.list_closed(**run_filter.to_filter_kwargs())

        return await self._compute_comparison(baseline_run_id, trades_a, run_filter)
