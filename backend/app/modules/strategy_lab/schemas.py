"""Strategy Lab REST schemas — request/response models."""

from datetime import date, datetime

from pydantic import BaseModel

# ======================================================================
# Request models
# ======================================================================


class CreateExperimentRequest(BaseModel):
    """Create a new experiment."""

    name: str
    description: str | None = None
    hypothesis: str | None = None


class CreateStrategyVersionRequest(BaseModel):
    """Create a new strategy version."""

    strategy_id: int
    parameters: dict | None = None
    change_log: str | None = None


class CreateRunRequest(BaseModel):
    """Create (execute) a new run.

    ``filters`` is a dict compatible with ``AnalyticsFilter`` fields.
    ``date_from`` and ``date_to`` are convenience overrides that take
    precedence over any dates inside ``filters``.
    """

    experiment_id: int | None = None
    strategy_version_id: int
    filters: dict
    baseline_run_id: int | None = None
    date_from: date | None = None
    date_to: date | None = None


# ======================================================================
# Response models
# ======================================================================


class StrategyVersionResponse(BaseModel):
    """Strategy version detail."""

    id: int
    strategy_id: int
    version: int
    parameters: dict | None
    rules_hash: str | None
    change_log: str | None
    created_at: datetime


class ExperimentResponse(BaseModel):
    """Experiment detail with computed ``run_count``."""

    id: int
    name: str
    description: str | None
    hypothesis: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    run_count: int = 0


class RunMetricResponse(BaseModel):
    """A single computed metric from a run."""

    id: int
    metric_name: str
    metric_value: float
    ci_lower: float | None
    ci_upper: float | None
    p_value: float | None
    effect_size: float | None
    parameters: dict | None


class RunResponse(BaseModel):
    """Full run detail with embedded metrics."""

    id: int
    experiment_id: int | None
    strategy_version_id: int
    engine_version: str
    dataset_snapshot_id: str
    parameters: dict
    filters: dict
    date_from: date
    date_to: date
    baseline_run_id: int | None
    status: str
    error_message: str | None
    created_at: datetime
    metrics: list[RunMetricResponse] = []


class ComparisonResponse(BaseModel):
    """A/B comparison of two runs."""

    run_a: RunResponse
    run_b: RunResponse
    results: list
