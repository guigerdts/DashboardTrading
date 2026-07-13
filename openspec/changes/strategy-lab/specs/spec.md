# Spec: Strategy Lab — Scientific Experiment Framework (v1.6.0)

## Related Files

| File | Role |
|------|------|
| `openspec/changes/strategy-lab/proposal.md` | Change proposal — intent, scope, risks, PR plan |
| `openspec/changes/strategy-lab/exploration.md` | Codebase exploration — existing patterns reused |
| `backend/app/models/strategy.py` | Existing `Strategy` catalog entity — FK target for `StrategyVersion` |
| `backend/app/modules/edge_discovery/interface/statistics_engine.py` | Interface pattern reused for `ComparisonEngine` |
| `backend/app/modules/edge_discovery/implementations/numpy_statistics_engine.py` | Bootstrap CI + p-value implementation reused |
| `backend/app/modules/analytics/service.py` | `AnalyticsService` — called during run execution |
| `backend/app/modules/analytics/schemas.py` | `AnalyticsFilter` — frozen with run params |

---

## Terminology

| Term | Definition |
|------|------------|
| **Strategy** | A named trading plan from the existing catalog (`strategies` table) |
| **StrategyVersion** | A versioned snapshot of a strategy's parameterization |
| **Experiment** | A hypothesis about strategy performance (contains Runs) |
| **Run** | A single immutable execution of a StrategyVersion against a frozen dataset |
| **RunMetric** | An expensive-to-compute metric result stored alongside a Run |
| **Dataset Snapshot** | A reference to the set of trades used (snapshot ID or trade ID list) |
| **ComparisonEngine** | Interface for statistical comparison between two Runs |

---

## User-Adjusted Scope (OVERRIDES proposal)

These 6 adjustments were approved by the user after the proposal and take precedence where they conflict:

1. **StrategyVersion** SHALL reference existing Strategy via FK to `strategies.id`. No parallel strategy hierarchy.
2. **Run** MUST be fully reproducible — every Run stores: `strategy_version_id`, `engine_version`, `dataset_snapshot_id`, `parameters` (JSON), `filters` (JSON), `date_range`, `created_at` timestamp.
3. **RunMetric** SHALL store ONLY expensive results — never metrics reconstructible from the snapshot (basic PF, win_rate, expectancy). Only store: bootstrapped CI of difference, permutation p-value, confidence level, cost-to-compute aggregates.
4. **Engine Version Capture** is MANDATORY and AUTOMATIC — must capture analytics engine version at run time. Not optional, not manual.
5. **Bootstrap CI + permutation test** SHALL be behind an interface — same pattern as `AbstractStatisticsEngine` in Edge Discovery. Domain depends on interface, not implementation.
6. **Run** is IMMUTABLE — never modified. Re-execution always creates a new Run.

---

## Module Structure

```
backend/app/modules/strategy_lab/
├── __init__.py
├── models.py              # StrategyVersion, Experiment, Run, RunMetric ORM models
├── schemas.py             # Pydantic request/response schemas
├── service.py             # Orchestration service (execute, compare, query)
├── router.py              # FastAPI REST endpoints
├── dependencies.py        # DI providers
├── interface/             # Abstraction layer
│   ├── __init__.py
│   └── comparison_engine.py  # ComparisonEngine ABC
├── implementations/
│   ├── __init__.py
│   └── bootstrap_comparison_engine.py  # Bootstrap CI + permutation test
└── version.py             # Engine version capture module
```

---

## R1: StrategyVersion Entity

### Description

A `StrategyVersion` captures a parameterized version of a Strategy catalog record. It stores the strategy logic as a rules hash plus the specific parameters tested. Creating a version does NOT modify the Strategy row. The `active_version_id` on Strategy is an optional FK set manually.

### Data Model

```python
class StrategyVersion(Base, TimestampMixin):
    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[str] = mapped_column(Text, nullable=False)   # JSON blob
    rules_hash: Mapped[str] = mapped_column(Text, nullable=False)    # SHA-256 of logic description
    setup_ids: Mapped[str] = mapped_column(Text, nullable=False)     # JSON list of setup IDs
    change_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("strategy_id", "version", name="uq_strategy_versions_strategy_version"),
    )
```

**Strategy model modification** (add nullable FK — single column):

```python
# On existing Strategy model:
active_version_id: Mapped[int | None] = mapped_column(
    ForeignKey("strategy_versions.id", ondelete="SET NULL"),
    nullable=True,
)
```

### Rules

- `version` SHALL auto-increment per strategy (max existing + 1). First version for a strategy = 1.
- `parameters` MUST be valid JSON. Stored as text blob — no schema enforced at DB level.
- `rules_hash` MUST be `SHA-256` of the human-readable strategy logic description. This is NOT a code hash — it's a deterministic fingerprint of what the strategy does.
- `setup_ids` MUST be a valid JSON list of `setup.id` values (M:N relationship frozen at version time).
- Creating a `StrategyVersion` MUST NOT modify the `Strategy` row.
- `Strategy.active_version_id` is set manually by the user — never set automatically on creation.
- On `Strategy` soft-delete, `StrategyVersion` records remain (ON DELETE CASCADE on strategy_id removes them on hard delete only; soft-delete keeps them accessible via Strategy.id).

### Validation Rules

- `strategy_id` MUST reference an existing, active Strategy (is_active = 1).
- `parameters` MUST be non-empty dict.
- `rules_hash` MUST be a valid 64-character hex string.
- Duplicate (strategy_id, version) MUST be rejected — UNIQUE constraint.

### API Contract

```
POST   /api/v1/strategy-lab/strategies/{strategy_id}/versions        → Create version
GET    /api/v1/strategy-lab/strategies/{strategy_id}/versions         → List versions
GET    /api/v1/strategy-lab/strategies/{strategy_id}/versions/{id}    → Get version detail
PATCH  /api/v1/strategy-lab/strategies/{strategy_id}                  → Set active_version_id
```

### Scenarios

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| R1-H1 | Happy path — create version | Strategy exists with id=1 | POST valid parameters, rules_hash, setup_ids | Returns 201 with version=1, created_at set |
| R1-H2 | Version monotonic per strategy | Version 1 exists for strategy 1 | POST a second version | Returns 201 with version=2 |
| R1-H3 | Parallel versions across strategies | Strategy 1 has version 2, Strategy 2 has version 1 | POST first version for Strategy 2 | Returns 201 with version=1 (independent counter) |
| R1-E1 | Invalid strategy | strategy_id=9999 | POST with valid payload | Returns 404 |
| R1-E2 | Soft-deleted strategy | Strategy has is_active=0 | POST | Returns 404 (active check) |
| R1-E3 | Duplicate version | Strategy 1 already has version 1 | POST with same (strategy_id, version) | Returns 409 — UNIQUE constraint violation |
| R1-E4 | Invalid rules_hash | rules_hash = "abc" | POST | Returns 422 — not 64 hex chars |

---

## R2: Experiment Entity

### Description

An `Experiment` groups multiple Runs under a single scientific hypothesis. This is the user-facing container for the Strategy Lab workflow: define a hypothesis, create parameter/filter variants, execute runs, compare results.

### Data Model

```python
class Experiment(Base, TimestampMixin):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(  # draft | running | completed | aborted
        Text,
        nullable=False,
        default="draft",
    )
```

### Status State Machine

```
draft ──→ running ──→ completed
             │
             └──→ aborted
```

- `draft`: Experiment created, no runs yet.
- `running`: At least one Run is currently executing. Set automatically when first run starts.
- `completed`: All runs completed successfully. Set automatically when all runs finish.
- `aborted`: Experiment manually cancelled by user. Runs already executed remain readable.

**Transition rule**: `running` → `completed` only when ALL runs have status = "completed" or "failed". `running` → `aborted` is manual and immediate.

### Validation Rules

- `name` MUST be non-empty, max 255 chars.
- `status` MUST be one of: `draft`, `running`, `completed`, `aborted`.
- Status transitions MUST follow the defined state machine.

### API Contract

```
POST   /api/v1/strategy-lab/experiments                       → Create experiment
GET    /api/v1/strategy-lab/experiments                        → List experiments (with run count)
GET    /api/v1/strategy-lab/experiments/{id}                   → Get experiment detail
PATCH  /api/v1/strategy-lab/experiments/{id}                   → Update name/description/hypothesis
POST   /api/v1/strategy-lab/experiments/{id}/abort             → Abort experiment
```

### Scenarios

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| R2-H1 | Happy path — create | — | POST with name, description, hypothesis | Returns 201, status="draft" |
| R2-H2 | Happy path — list empty | No experiments exist | GET /experiments | Returns 200 with empty list |
| R2-H3 | Abort running experiment | Experiment in "running" with 2 completed runs | POST /abort | Status = "aborted", existing runs readable |
| R2-E1 | Invalid status transition | Experiment is "completed" | POST /abort | Returns 422 — cannot abort completed experiment |
| R2-E2 | Empty name | — | POST with name="" | Returns 422 |

---

## R3: Run Entity (IMMUTABLE)

### Description

A `Run` is a single immutable execution of a `StrategyVersion` against a frozen dataset. Every detail required to reproduce the run is stored inline. Runs are NEVER modified after creation — re-execution with the same config creates a new Run with a new ID.

### Data Model

```python
class Run(Base):
    """Immutable run record — NEVER updated or deleted."""
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(
        ForeignKey("experiments.id", ondelete="CASCADE"),
        nullable=False,
    )
    strategy_version_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    engine_version: Mapped[str] = mapped_column(Text, nullable=False)     # MANDATORY, auto-captured
    dataset_snapshot_id: Mapped[str] = mapped_column(Text, nullable=False)  # Reference to trade snapshot
    parameters: Mapped[str] = mapped_column(Text, nullable=False)           # JSON blob
    filters: Mapped[str] = mapped_column(Text, nullable=False)              # JSON blob (AnalyticsFilter)
    date_from: Mapped[str | None] = mapped_column(Text, nullable=True)      # ISO date
    date_to: Mapped[str | None] = mapped_column(Text, nullable=True)        # ISO date
    baseline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(  # running | completed | failed
        Text,
        nullable=False,
        default="running",
    )
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)

    __table_args__ = (
        sa.UniqueConstraint(
            "strategy_version_id", "parameters", "filters",
            "date_from", "date_to", "engine_version",
            name="uq_runs_config_identity",
        ),
    )
```

### Immutability Contract

- **NO UPDATE** SQL operations on `runs` table after row insertion.
- **NO DELETE** SQL operations on `runs` table at application level.
- Only `status` MAY be updated: `running` → `completed` or `running` → `failed`.
- All other columns SHALL remain read-only after creation.
- Repository layer SHALL expose `save` and `get` but NO `update` or `delete` methods for runs.
- Router MUST NOT expose PUT/PATCH/DELETE endpoints for runs (except PATCH status).
- If re-execution is needed with identical config, the UNIQUE constraint catches it — use different parameters, filters, or date range.

### Config Identity Rule

The UNIQUE constraint on `(strategy_version_id, parameters, filters, date_from, date_to, engine_version)` means:

- Same strategy version + same parameters + same filters + same date range + same engine version = **same run identity**.
- A second attempt with identical config returns the existing Run ID with status.
- To re-execute, the user MUST change at least one of: parameters, filters, date range, or create a new strategy version.

### Validation Rules

- `strategy_version_id` MUST reference an existing `StrategyVersion`.
- `experiment_id` MUST reference an existing `Experiment`.
- `engine_version` MUST be non-empty (auto-captured — never user-supplied).
- `dataset_snapshot_id` MUST be non-empty.
- `date_from` and `date_to` MUST be valid ISO dates when provided.
- `parameters` MUST be valid JSON.
- `filters` MUST be valid JSON that deserializes to `AnalyticsFilter` fields.

### API Contract

```
POST   /api/v1/strategy-lab/runs                              → Execute run (creates + runs)
GET    /api/v1/strategy-lab/runs                               → List runs (with pagination + filters)
GET    /api/v1/strategy-lab/runs/{id}                          → Get run detail with metrics
PATCH  /api/v1/strategy-lab/runs/{id}/status                   → Update status only (running→completed|failed)
```

### Scenarios

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| R3-H1 | Happy path — create and run | Valid strategy version, experiment, snapshot exists | POST with valid config | Returns 201, status="running" → completes, status="completed" |
| R3-H2 | Duplicate config | Run exists with exact same config | POST identical payload | Returns 200 with existing Run ID (config identity) |
| R3-H3 | Immutability enforced | Completed run | PATCH body fields other than status | Returns 422 |
| R3-H4 | Baseline run reference | Two runs created, one set as baseline | POST with baseline_run_id | Returns 201, baseline FK set |
| R3-E1 | Invalid strategy version | strategy_version_id=9999 | POST | Returns 404 |
| R3-E2 | Invalid experiment | experiment_id=9999 | POST | Returns 404 |
| R3-E3 | Deleted baseline | baseline_run_id references non-existent run | POST | Returns 404 |
| R3-E4 | Engine capture failure | Version module fails | POST | Returns 500, run not created |
| R3-E5 | Empty engine_version | engine_version="" (manual — prevented by auto-capture) | — | Constraint violation at DB level |

---

## R4: RunMetric Entity

### Description

`RunMetric` stores expensive-to-compute metric results for a Run. Only stores results that CANNOT be reconstructed from the dataset snapshot + analytics service. Basic metrics (PF, win_rate, expectancy, avg_r, drawdown, Sharpe) are NEVER persisted — they are computed on-the-fly from the snapshot.

### Data Model

```python
class RunMetric(Base):
    __tablename__ = "run_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_interval_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_interval_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    parameters: Mapped[str | None] = mapped_column(Text, nullable=True)   # JSON — e.g. bootstrap params
```

### What to Store (IN RunMetric) vs. NOT Store

| Store in RunMetric | DO NOT Store (reconstruct from snapshot) |
|---|---|
| Bootstrap CI of difference between two runs | Profit Factor |
| Permutation test p-value | Win Rate |
| Confidence level (high/medium/low) | Expectancy |
| Bootstrapped Sharpe distribution stats | Avg R Multiple |
| Effect size (Cohen's d, Hedges' g) | Max Drawdown |
| Cost-to-compute aggregates (>1s runtime) | Sharpe Ratio (single) |
| Any statistical result involving bootstrap | Sortino Ratio |
| Any result comparing two or more runs | Calmar Ratio |
| | Payoff Ratio |
| | Recovery Factor |
| | R Distribution |
| | Equity curve points |
| | PnL by period |

### Rationale

The `AnalyticsService` can reconstruct all "Do Not Store" metrics from the filtered trade list. The dataset snapshot reference (`dataset_snapshot_id`) is available per Run, so those metrics are always recomputable. RunMetric exists ONLY to capture statistical results that require comparison, resampling, or aggregation that the AnalyticsService cannot produce from a single trade list.

### Validation Rules

- `run_id` MUST reference an existing Run.
- `metric_name` MUST be non-empty, max 100 chars.
- `metric_value` MUST be a finite float.
- Only metrics from the "Store in RunMetric" list SHALL be persisted.

### API Contract

```
GET    /api/v1/strategy-lab/runs/{id}/metrics               → List metrics for a run (read-only)
```

No POST/PUT/DELETE for metrics — created automatically during run execution.

### Scenarios

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| R4-H1 | Metrics created after run | Run exists with status="completed" | GET /runs/{id}/metrics | Returns list of metrics (may be empty) |
| R4-H2 | No expensive metrics | Simple run with no comparison | GET /runs/{id}/metrics | Returns empty list (no expensive metrics needed) |
| R4-H3 | Comparison metrics stored | Two runs compared | POST /comparison | RunMetric created with CI, p-value |
| R4-E1 | Metric for non-existent run | run_id=9999 | GET /runs/9999/metrics | Returns 404 |
| R4-E2 | Attempt to store basic metric | Service tries to save "win_rate" | — | Rejected by storage layer |

---

## R5: Engine Version Capture (AUTOMATIC, MANDATORY)

### Description

Engine version MUST be captured automatically at run time and stored in `Run.engine_version`. This is NOT optional and NOT user-supplied. The mechanism reads the analytics engine version from a dedicated version module.

### Mechanism

```python
# backend/app/modules/strategy_lab/version.py

"""Engine version capture — automatic, mandatory.

Reads the analytics engine version from an authoritative source.
Return value is stored in Run.engine_version for all runs.
"""

from importlib.metadata import version as _pkg_version

_ENGINE_VERSION: str | None = None


def _detect_version() -> str:
    """Detect analytics engine version from installed package metadata."""
    try:
        return _pkg_version("analytics-engine")  # or appropriate package name
    except Exception:
        pass
    try:
        # Fallback: git describe
        import subprocess
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            capture_output=True, text=True, timeout=5,
            cwd=...  # project root
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    raise RuntimeError(
        "Cannot determine analytics engine version. "
        "Run execution requires a detectable engine version."
    )


def get_engine_version() -> str:
    """Return the cached analytics engine version.

    Raises RuntimeError if version cannot be determined.
    """
    global _ENGINE_VERSION
    if _ENGINE_VERSION is None:
        _ENGINE_VERSION = _detect_version()
    return _ENGINE_VERSION
```

**Integration**:

```python
# In run execution service:
from app.modules.strategy_lab.version import get_engine_version

def execute_run(...) -> Run:
    engine_version = get_engine_version()  # Raises RuntimeError if fails
    # ... create Run with engine_version ...
```

### Rules

- `get_engine_version()` SHALL be called at run creation time, inside the service layer.
- The result SHALL be stored in `Run.engine_version`.
- If `get_engine_version()` raises `RuntimeError`, the Run MUST NOT be created — the request fails with 500.
- The version string MUST be human-readable and traceable to a specific build.
- Detection order: (1) `importlib.metadata.version`, (2) `git describe --always --dirty`.
- Lazy caching: version is detected once per process lifecycle.

### Scenarios

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| R5-H1 | Package version found | Package metadata available | `get_engine_version()` | Returns version string from package |
| R5-H2 | Git fallback | No package, git available | `get_engine_version()` | Returns git describe output |
| R5-H3 | Cached after first call | Already detected | Second call | Returns same string (cached) |
| R5-E1 | No version source | No package, no git | `get_engine_version()` | Raises RuntimeError |
| R5-V1 | Version in Run | Run created | Check engine_version | Non-null, non-empty |

---

## R6: StrategyComparisonEngine

### Description

Interface for statistical comparison between two Runs. Same pattern as `AbstractStatisticsEngine` in Edge Discovery — domain depends on the interface, implementations provide the computation. The reference implementation uses bootstrap CI of the difference and permutation test.

### Interface

```python
# backend/app/modules/strategy_lab/interface/comparison_engine.py

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ComparisonResult:
    """Result of comparing two runs on a single metric."""
    metric_name: str
    diff_mean: float                     # mean(run_a_metric) - mean(run_b_metric)
    ci_lower: float                      # Lower bound of bootstrap CI of the difference
    ci_upper: float                      # Upper bound of bootstrap CI of the difference
    p_value: float                       # Permutation test p-value
    confidence: float                    # Confidence level used (e.g., 0.95)
    effect_size: float | None = None     # Cohen's d or similar


class ComparisonEngine(ABC):
    """Statistical comparison between two runs.

    All methods are pure functions — no side effects, no state.
    Implementations may use numpy, scipy, or pure Python.
    """

    @abstractmethod
    def compare_metric(
        self,
        values_a: list[float],
        values_b: list[float],
        metric_name: str = "",
        n_resamples: int = 10_000,
        confidence: float = 0.95,
        seed: int | None = None,
    ) -> ComparisonResult:
        """Compare two sets of metric values using bootstrap CI + permutation test.

        Parameters
        ----------
        values_a : list[float]
            Per-trade metric values from run A.
        values_b : list[float]
            Per-trade metric values from run B.
        metric_name : str
            Name of the metric being compared.
        n_resamples : int
            Number of bootstrap/permutation resamples.
        confidence : float
            Confidence level for CI (e.g., 0.95).
        seed : int or None
            Random seed for reproducibility.

        Returns
        -------
        ComparisonResult
            Difference CI, p-value, effect size.
        """

    @abstractmethod
    def compare_multiple(
        self,
        values_a: list[float],
        values_b: list[float],
        metrics: list[str],
        n_resamples: int = 10_000,
        confidence: float = 0.95,
        seed: int | None = None,
    ) -> list[ComparisonResult]:
        """Compare multiple metrics between two runs.

        Each metric is compared independently.
        Returns one ComparisonResult per metric.
        """
```

### Implementation: BootstrapComparisonEngine

```python
# backend/app/modules/strategy_lab/implementations/bootstrap_comparison_engine.py

class BootstrapComparisonEngine(ComparisonEngine):
    """Comparison engine using bootstrap CI of difference + permutation test.

    Reuses concepts from edge discovery's NumpyStatisticsEngine.
    """

    def compare_metric(
        self,
        values_a: list[float],
        values_b: list[float],
        metric_name: str = "",
        n_resamples: int = 10_000,
        confidence: float = 0.95,
        seed: int | None = None,
    ) -> ComparisonResult:
        # 1. Compute observed difference of means
        # 2. Bootstrap CI of the difference: resample both with replacement,
        #    compute difference each time, get percentiles
        # 3. Permutation test: shuffle labels, recompute difference,
        #    p = proportion of permuted diffs >= observed
        # 4. Compute Cohen's d effect size
        ...
```

### DI Wiring

```python
# dependencies.py
from app.modules.strategy_lab.interface.comparison_engine import ComparisonEngine
from app.modules.strategy_lab.implementations.bootstrap_comparison_engine import BootstrapComparisonEngine

async def get_comparison_engine() -> ComparisonEngine:
    return BootstrapComparisonEngine()
```

### Scenarios

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| R6-H1 | Two runs with clear difference | Run A expectancy=2.0, Run B=0.5 | compare_metric(expectancy) | CI does not include 0, p_value < 0.05 |
| R6-H2 | Two identical runs | Same metric values | compare_metric() | CI includes 0, p_value ≈ 1.0 |
| R6-H3 | Effect size reported | Large difference | compare_metric() | effect_size != None |
| R6-E1 | Empty values | values_a=[] | compare_metric() | Returns result with diff_mean=0, p_value=1.0 |
| R6-E2 | Single trade each | values_a=[1.0], values_b=[2.0] | compare_metric() | Still computes (degenerate CI expected) |
| R6-I1 | Interface swap | New implementation added | Inject new class | Works without service changes |

---

## R7: Run Execution

### Description

Synchronous execution of a `StrategyVersion` against a dataset snapshot. The service freezes the filters and date range, calls the `AnalyticsService` to compute base metrics (but does NOT store them), then stores only expensive RunMetrics.

### Execution Flow

```
execute_run(strategy_version_id, experiment_id, filters, date_range):
  │
  ├─ 1. Validate inputs
  │   ├─ strategy_version exists
  │   ├─ experiment exists
  │   ├─ filters + date_range valid
  │
  ├─ 2. Capture engine version (MANDATORY)
  │   └─ get_engine_version()  ← raises RuntimeError if fails
  │
  ├─ 3. Create Run record (status=running)
  │   ├─ engine_version, dataset_snapshot_id, parameters, filters
  │   ├─ date_from, date_to, baseline_run_id (if any)
  │   └─ UNIQUE constraint check → duplicate returns existing
  │
  ├─ 4. Execute analytics
  │   ├─ Call AnalyticsService with frozen filters + date range
  │   └─ Compute all analytics metrics
  │
  ├─ 5. Store expensive RunMetrics
  │   ├─ Compare with baseline (if baseline_run_id set)
  │   └─ Store CI, p-value, confidence, effect size
  │
  ├─ 6. Update Run status → "completed"
  │
  └─ Return Run ID + "completed"
```

### Error Recovery

| Failure Point | Behavior |
|---------------|----------|
| Engine version capture fails | Run NOT created, 500 returned |
| Unique constraint violation | Return existing Run ID + "completed" status |
| AnalyticsService failure | Run status → "failed", error logged, 500 returned |
| Partial metrics stored | Run status → "failed" (metrics rolled back with transaction) |

### Key Design Decision

Run execution is synchronous because:
- Metrics calculation is fast (pure computation over DataFrame from UoW).
- No blocking I/O after trade fetch.
- User expects immediate result in the Strategy Lab context.
- Background tasks add complexity for run status polling.

### API Contract

```
POST   /api/v1/strategy-lab/runs                              → Execute run
  Body: { strategy_version_id, experiment_id, filters, date_from, date_to, baseline_run_id? }
  Returns: { id, status, duplicate_of? }
```

### Scenarios

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| R7-H1 | Full run execution | Valid strategy version + experiment | POST /runs | Run created, status="completed", metrics stored |
| R7-H2 | Duplicate config | Run already exists with same config | POST /runs | Returns existing Run ID, not a new one |
| R7-H3 | Run with baseline comparison | Valid baseline_run_id | POST /runs | RunMetrics include comparison results |
| R7-E1 | Invalid inputs | Bad strategy_version_id | POST /runs | Returns 404, no Run created |
| R7-E2 | Engine version not found | Version detection fails | POST /runs | Returns 500, no Run created |
| R7-E3 | Analytics failure | Downstream error | POST /runs | Run status="failed", 500 returned |

---

## R8: Frontend (MVP)

### Pages

**Experiment List** (`/strategy-lab`)
- Table of experiments with: name, hypothesis (truncated), status, run count, created_at
- "New Experiment" button → create modal/form
- Click row → navigate to experiment detail
- Empty state: "No experiments yet. Create your first experiment to test hypotheses about your trading strategies." + CTA button
- Loading state: Skeleton rows
- Error state: Alert with retry button
- Follow existing module patterns (React Query, loading/error/empty/success states)

**Run Detail** (`/strategy-lab/runs/{id}`)
- Header: Experiment name, strategy version, status badge
- Reproducibility info card: engine_version, dataset_snapshot_id, parameters (JSON formatted), filters, date range, created_at
- Metrics table: metric_name, metric_value, CI (lower–upper), p_value
  - Color-coded: green for significant (p < 0.05), gray for non-significant
- "Compare with..." dropdown (select another run in same experiment)
- Back button to experiment

**Comparison View** (`/strategy-lab/runs/{id}/compare?with={other_id}`)
- Two-column layout: Run A | Run B
- Metric rows: name, values side-by-side, delta column
- Delta column shows: diff_mean, CI [lower, upper], p-value
- Statistically significant differences highlighted
- "Not comparable" message if runs use different strategy versions or date ranges
- Reproducibility info for both runs shown

### Component Patterns

All pages SHALL follow the existing frontend module pattern:
- React Query for data fetching (useQuery, useMutation)
- Loading/Error/Empty/Success states on every data-dependent component
- TypeScript interfaces matching backend schemas
- Consistent spacing, colors, typography from the design system

### API Integration

```
GET    /api/v1/strategy-lab/experiments                          → List experiments
POST   /api/v1/strategy-lab/experiments                          → Create experiment
GET    /api/v1/strategy-lab/experiments/{id}                     → Get experiment detail
PATCH  /api/v1/strategy-lab/experiments/{id}                     → Update experiment
POST   /api/v1/strategy-lab/experiments/{id}/abort               → Abort experiment
GET    /api/v1/strategy-lab/runs                                  → List runs (with query params)
POST   /api/v1/strategy-lab/runs                                  → Execute run
GET    /api/v1/strategy-lab/runs/{id}                             → Get run detail with metrics
GET    /api/v1/strategy-lab/runs/{id}/metrics                     → List run metrics
POST   /api/v1/strategy-lab/runs/{id}/compare?with={other_id}    → Compare two runs
GET    /api/v1/strategy-lab/strategies/{id}/versions              → List strategy versions
POST   /api/v1/strategy-lab/strategies/{id}/versions              → Create strategy version
GET    /api/v1/strategy-lab/strategies/{id}/versions/{version_id} → Get version detail
PATCH  /api/v1/strategy-lab/strategies/{id}                       → Set active version
```

### Scenarios

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| R8-H1 | Experiment list — populated | Experiments exist with runs | Navigate to /strategy-lab | Table shows experiments with run counts |
| R8-H2 | Experiment list — empty | No experiments | Navigate to /strategy-lab | Empty state with CTA |
| R8-H3 | Run detail with metrics | Completed run with metrics | Navigate to /strategy-lab/runs/1 | Shows metrics table + reproducibility card |
| R8-H4 | Comparison view | Two runs in same experiment | Navigate to comparison | Side-by-side with CI and p-value |
| R8-E1 | Run not found | id=9999 | Navigate to /strategy-lab/runs/9999 | Error state: "Run not found" |
| R8-E2 | Comparison of unrelated runs | Different strategy versions | Try to compare | Warning: "Runs use different strategy versions" |
| R8-L1 | Loading states | Data not yet fetched | Navigate to any page | Skeleton/spinner displayed |
| R8-N1 | Create experiment | Empty form | Submit | Loading state → Success → Redirect to experiment |

---

## Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|-------------|
| AC-01 | Every Run has `strategy_version_id`, `engine_version`, `dataset_snapshot_id` — all non-null | SELECT COUNT(*) FROM runs WHERE any IS NULL = 0 |
| AC-02 | Existing analytics tests still pass | `cd backend && python -m pytest tests/analytics/` |
| AC-03 | Run is immutable — no UPDATE/DELETE routes | Router file grep for PUT/PATCH/DELETE on runs (status update excluded) |
| AC-04 | Engine version is captured automatically, never manual | No engine_version field in any POST/PATCH request schema |
| AC-05 | Comparison engine is behind `ComparisonEngine` interface | Service imports `ComparisonEngine` ABC, not `BootstrapComparisonEngine` directly |
| AC-06 | RunMetric only contains non-reconstructible metrics | All RunMetric creation calls checked — no basic metrics stored |
| AC-07 | Duplicate run config returns existing Run | Integration test: same POST body × 2 → same Run ID |
| AC-08 | StrategyVersion monotonically increments per strategy | Test: versions 1, 2, 3 for strategy 1; version 1 for strategy 2 |
| AC-09 | Experiment status state machine enforced | Test: all valid + invalid transitions |
| AC-10 | Frontend shows loading/error/empty/success states | Component tests for each page |
| AC-11 | No modifications to existing analytics, trade, or strategy models | `git diff --name-only` against existing models shows only strategy.py (add active_version_id FK) |

---

## Constraints

| Constraint | Rule |
|------------|------|
| Offline-first | All new tables in the existing `trading_journal.db` (SQLite behind UoW) |
| No journal modifications | Trade, Strategy, Analytics, Edge Discovery models remain untouched |
| No generative AI | All comparison logic is classical statistics (bootstrap + permutation) |
| No duplicating analytics | RunMetric does NOT duplicate any AnalyticsService output |
| ADR-008 traceability | All decisions in this spec are linked to exploration findings and user-approved adjustments |

## Migration Plan

```python
# alembic/versions/XXXX_strategy_lab_v1.py

"""Strategy Lab v1 — Experiment, Run, StrategyVersion, RunMetric tables.

Revision ID: XXXX
Revises: <previous_revision>
"""

def upgrade():
    # 1. Create strategy_versions table
    op.create_table("strategy_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parameters", sa.Text(), nullable=False),
        sa.Column("rules_hash", sa.Text(), nullable=False),
        sa.Column("setup_ids", sa.Text(), nullable=False),
        sa.Column("change_log", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("strategy_id", "version"),
    )

    # 2. Add active_version_id to strategies
    op.add_column("strategies",
        sa.Column("active_version_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_strategies_active_version_id_strategy_versions",
        "strategies", "strategy_versions",
        ["active_version_id"], ["id"],
        ondelete="SET NULL",
    )

    # 3. Create experiments table
    op.create_table("experiments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=True),
    )

    # 4. Create runs table
    op.create_table("runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=False),
        sa.Column("strategy_version_id", sa.Integer(), nullable=False),
        sa.Column("engine_version", sa.Text(), nullable=False),
        sa.Column("dataset_snapshot_id", sa.Text(), nullable=False),
        sa.Column("parameters", sa.Text(), nullable=False),
        sa.Column("filters", sa.Text(), nullable=False),
        sa.Column("date_from", sa.Text(), nullable=True),
        sa.Column("date_to", sa.Text(), nullable=True),
        sa.Column("baseline_run_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["strategy_version_id"], ["strategy_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["baseline_run_id"], ["runs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "strategy_version_id", "parameters", "filters",
            "date_from", "date_to", "engine_version",
        ),
    )

    # 5. Create run_metrics table
    op.create_table("run_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("confidence_interval_lower", sa.Float(), nullable=True),
        sa.Column("confidence_interval_upper", sa.Float(), nullable=True),
        sa.Column("p_value", sa.Float(), nullable=True),
        sa.Column("parameters", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
    )


def downgrade():
    op.drop_table("run_metrics")
    op.drop_constraint("fk_strategies_active_version_id_strategy_versions", "strategies")
    op.drop_column("strategies", "active_version_id")
    op.drop_table("runs")
    op.drop_table("experiments")
    op.drop_table("strategy_versions")
```

---

## PR Breakdown

| PR | LOC | Contents |
|----|-----|----------|
| PR #1 — Data Layer | ~400 | Models (`models.py`, modification to `strategy.py`), migration, `__init__.py` exports |
| PR #2 — Execution Engine | ~500 | Service, ComparisonEngine interface + Bootstrap implementation, version capture, dependencies |
| PR #3 — API Layer | ~350 | Router, schemas, integration tests, UoW updates |
| PR #4 — Frontend | ~450 | Experiment list, run detail, comparison view, hooks, component tests |

## ADR-008 Traceability

| Decision | Source | Section |
|----------|--------|---------|
| StrategyVersion FK to strategies.id | User adjustment #1 (overrides proposal) | R1 |
| Run stores all reproducibility fields | User adjustment #2 | R3 |
| RunMetric only stores expensive results | User adjustment #3 | R4 |
| Engine version mandatory + automatic | User adjustment #4 (overrides proposal's "optional") | R5 |
| ComparisonEngine behind interface | User adjustment #5 | R6 |
| Run is immutable | User adjustment #6 | R3 |
| No parallel strategy hierarchy | Exploration finding #1 — Strategy is simple catalog | R1 |
| JSON blob parameters | Exploration finding #2 — No parameter storage exists | R1 |
| Snapshot pattern from edge discovery | Exploration finding #3 — Edge Discovery has write-once pattern | R3 |
| AnalyticsService unchanged | Exploration finding #4 — Analytics is read-only, deterministic | R7 |
| NumpyStatisticsEngine reused | Exploration finding #5 — Bootstrap CI + p-value exist | R6 |
| Synchronous execution | Design decision: metrics calc is fast, no blocking I/O | R7 |
| Same DB (trading_journal.db) | Architecture constraint: offline-first | All |
