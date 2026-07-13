"""Strategy Lab REST API — experiment, run, and strategy-version lifecycle.

All creation endpoints apply business rules through ``StrategyLabService``.
Read endpoints use the UnitOfWork directly for simple queries.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError
from app.db.dependencies import get_uow
from app.db.unit_of_work import UnitOfWork
from app.modules.analytics.schemas import AnalyticsFilter
from app.modules.strategy_lab.dependencies import get_strategy_lab_service
from app.modules.strategy_lab.schemas import (
    ComparisonResponse,
    CreateExperimentRequest,
    CreateRunRequest,
    CreateStrategyVersionRequest,
    ExperimentResponse,
    RunMetricResponse,
    RunResponse,
    StrategyVersionResponse,
)
from app.modules.strategy_lab.service import StrategyLabService

router = APIRouter(prefix="/api/strategy-lab", tags=["strategy-lab"])


# ======================================================================
# Helper — convert ORM models to Pydantic responses
# ======================================================================


def _sv_to_response(sv) -> StrategyVersionResponse:
    return StrategyVersionResponse(
        id=sv.id,
        strategy_id=sv.strategy_id,
        version=sv.version,
        parameters=sv.parameters,
        rules_hash=sv.rules_hash,
        change_log=sv.change_log,
        created_at=sv.created_at,
    )


def _exp_to_response(exp, run_count: int = 0) -> ExperimentResponse:
    return ExperimentResponse(
        id=exp.id,
        name=exp.name,
        description=exp.description,
        hypothesis=exp.hypothesis,
        status=exp.status,
        created_at=exp.created_at,
        updated_at=exp.updated_at,
        run_count=run_count,
    )


def _metric_to_response(m) -> RunMetricResponse:
    return RunMetricResponse(
        id=m.id,
        metric_name=m.metric_name,
        metric_value=m.metric_value,
        ci_lower=m.ci_lower,
        ci_upper=m.ci_upper,
        p_value=m.p_value,
        effect_size=m.effect_size,
        parameters=m.parameters,
    )


def _run_to_response(run, metrics: list | None = None) -> RunResponse:
    return RunResponse(
        id=run.id,
        experiment_id=run.experiment_id,
        strategy_version_id=run.strategy_version_id,
        engine_version=run.engine_version,
        dataset_snapshot_id=run.dataset_snapshot_id,
        parameters=run.parameters,
        filters=run.filters,
        date_from=run.date_from,
        date_to=run.date_to,
        baseline_run_id=run.baseline_run_id,
        status=run.status,
        error_message=run.error_message,
        created_at=run.created_at,
        metrics=[_metric_to_response(m) for m in (metrics or [])],
    )


# ======================================================================
# Strategy Version endpoints
# ======================================================================


@router.get("/strategy-versions", response_model=list[StrategyVersionResponse])
async def list_strategy_versions(
    strategy_id: int = Query(..., description="Strategy ID to list versions for"),
    uow: UnitOfWork = Depends(get_uow),
):
    """List all versions for a given strategy."""
    items, _ = await uow.strategy_versions.list(strategy_id=strategy_id)
    return [_sv_to_response(sv) for sv in items]


@router.post(
    "/strategy-versions",
    response_model=StrategyVersionResponse,
    status_code=201,
)
async def create_strategy_version(
    body: CreateStrategyVersionRequest,
    service: StrategyLabService = Depends(get_strategy_lab_service),
):
    """Create a new version for a strategy (auto-incrementing version)."""
    sv = await service.create_strategy_version(
        strategy_id=body.strategy_id,
        parameters=body.parameters,
        change_log=body.change_log,
    )
    return _sv_to_response(sv)


@router.get(
    "/strategy-versions/{version_id}",
    response_model=StrategyVersionResponse,
)
async def get_strategy_version(
    version_id: int,
    uow: UnitOfWork = Depends(get_uow),
):
    """Get a single strategy version by ID."""
    sv = await uow.strategy_versions.get(version_id)
    if sv is None:
        raise NotFoundError(f"StrategyVersion {version_id} not found")
    return _sv_to_response(sv)


# ======================================================================
# Experiment endpoints
# ======================================================================


@router.get("/experiments", response_model=list[ExperimentResponse])
async def list_experiments(
    service: StrategyLabService = Depends(get_strategy_lab_service),
):
    """List all experiments."""
    exps = await service.list_experiments()
    return [_exp_to_response(exp) for exp in exps]


@router.post("/experiments", response_model=ExperimentResponse, status_code=201)
async def create_experiment(
    body: CreateExperimentRequest,
    service: StrategyLabService = Depends(get_strategy_lab_service),
):
    """Create a new experiment in draft status."""
    exp = await service.create_experiment(
        name=body.name,
        description=body.description,
        hypothesis=body.hypothesis,
    )
    return _exp_to_response(exp)


@router.get(
    "/experiments/{experiment_id}",
    response_model=ExperimentResponse,
)
async def get_experiment(
    experiment_id: int,
    service: StrategyLabService = Depends(get_strategy_lab_service),
):
    """Get an experiment with its computed run count."""
    exp = await service.get_experiment(experiment_id)
    if exp is None:
        raise NotFoundError(f"Experiment {experiment_id} not found")
    run_count = await service.count_runs_for_experiment(experiment_id)
    return _exp_to_response(exp, run_count=run_count)


@router.delete(
    "/experiments/{experiment_id}",
    status_code=204,
)
async def delete_experiment(
    experiment_id: int,
    service: StrategyLabService = Depends(get_strategy_lab_service),
):
    """Delete an experiment. Rejects if runs still reference it."""
    exp = await service.get_experiment(experiment_id)
    if exp is None:
        raise NotFoundError(f"Experiment {experiment_id} not found")

    run_count = await service.count_runs_for_experiment(experiment_id)
    if run_count > 0:
        raise ConflictError(f"Cannot delete experiment {experiment_id}: it has {run_count} run(s)")

    await service.delete_experiment(experiment_id)


# ======================================================================
# Run endpoints
# ======================================================================


@router.get("/runs", response_model=list[RunResponse])
async def list_runs(
    service: StrategyLabService = Depends(get_strategy_lab_service),
):
    """List all runs."""
    runs = await service.list_runs()
    # Fetch metrics for each run
    results = []
    for run in runs:
        metrics = await service.get_run_metrics(run.id)
        results.append(_run_to_response(run, metrics=metrics))
    return results


@router.post("/runs", response_model=RunResponse, status_code=201)
async def create_run(
    body: CreateRunRequest,
    service: StrategyLabService = Depends(get_strategy_lab_service),
):
    """Create (execute) a new run.

    Converts the raw ``filters`` dict + optional ``date_from``/``date_to``
    into an ``AnalyticsFilter``, then delegates to ``StrategyLabService``.
    """
    # Build AnalyticsFilter from request
    filter_kwargs = dict(body.filters)
    if body.date_from is not None:
        filter_kwargs["date_from"] = datetime.combine(body.date_from, datetime.min.time())
    if body.date_to is not None:
        filter_kwargs["date_to"] = datetime.combine(body.date_to, datetime.max.time())
    filters = AnalyticsFilter(**filter_kwargs)

    try:
        run = await service.create_run(
            experiment_id=body.experiment_id,
            strategy_version_id=body.strategy_version_id,
            filters=filters,
            baseline_run_id=body.baseline_run_id,
        )
    except IntegrityError:
        raise ConflictError("Duplicate run configuration")

    # Fetch metrics created by the service
    metrics = await service.get_run_metrics(run.id)
    return _run_to_response(run, metrics=metrics)


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
)
async def get_run(
    run_id: int,
    service: StrategyLabService = Depends(get_strategy_lab_service),
):
    """Get a single run with its metrics."""
    run = await service.get_run(run_id)
    if run is None:
        raise NotFoundError(f"Run {run_id} not found")
    metrics = await service.get_run_metrics(run.id)
    return _run_to_response(run, metrics=metrics)


@router.get(
    "/runs/{run_id}/compare",
    response_model=ComparisonResponse,
)
async def compare_runs(
    run_id: int,
    baseline_id: int = Query(..., description="Baseline run ID"),
    service: StrategyLabService = Depends(get_strategy_lab_service),
):
    """Compare a run against a baseline run.

    Returns both runs' full data plus ``ComparisonResult`` dicts.
    """
    run_a = await service.get_run(run_id)
    if run_a is None:
        raise NotFoundError(f"Run {run_id} not found")

    run_b = await service.get_run(baseline_id)
    if run_b is None:
        raise NotFoundError(f"Baseline run {baseline_id} not found")

    try:
        comparison_result = await service.get_comparison(run_id, baseline_id)
    except NotFoundError:
        raise HTTPException(status_code=404, detail="Comparison failed: one or both runs not found")

    metrics_a = await service.get_run_metrics(run_a.id)
    metrics_b = await service.get_run_metrics(run_b.id)

    return ComparisonResponse(
        run_a=_run_to_response(run_a, metrics=metrics_a),
        run_b=_run_to_response(run_b, metrics=metrics_b),
        results=[dataclasses.asdict(comparison_result)],
    )
