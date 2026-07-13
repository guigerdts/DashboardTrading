# Design: Strategy Lab — Scientific Experiment Framework (v1.6.0)

## Lead

Strategy Lab adds a scientific experimentation framework to DashboardTrading: version-traceable strategy snapshots, immutable backtest Runs with auto-captured engine version, statistical comparison via bootstrap CI/permutation test behind a pluggable interface, and a UI for designing experiments, reviewing results, and comparing runs side by side.

Four new tables (`strategy_versions`, `experiments`, `runs`, `run_metrics`), one new module (`strategy_lab`), one FK field on `Strategy`. The `AnalyticsService` is called but unchanged. Zero modifications to existing trade, analytics, or edge discovery models.

---

## User-Adjusted Design Decisions (non-negotiable — override proposal)

| # | Decision | Rule |
|---|----------|------|
| 1 | **StrategyVersion FK** | `strategy_id` FK to `strategies.id`. No parallel hierarchy. Strategy catalog only gets `active_version_id` nullable FK. |
| 2 | **Run fully reproducible** | Stores: `strategy_version_id`, `engine_version`, `dataset_snapshot_id`, `parameters` (JSON), `filters` (JSON), `date_from`, `date_to`, `created_at`. ALL mandatory. |
| 3 | **RunMetric stores ONLY expensive results** | Bootstrapped CI of difference, permutation p-value, confidence, effect size. NOT basic metrics (PF, win_rate, expectancy, sharpe, drawdown). |
| 4 | **Engine version MANDATORY, AUTOMATIC** | Not optional, not manual. `importlib.metadata` or `git describe` at runtime. Run creation fails if version can't be captured. |
| 5 | **ComparisonEngine behind interface** | `ComparisonEngine(ABC)` same pattern as `AbstractStatisticsEngine` in edge discovery. `BootstrapComparisonEngine` is the implementation. |
| 6 | **Run IMMUTABLE** | No UPDATE/DELETE. Re-execution = new Run. Config identity UNIQUE constraint prevents duplicates. |

---

## 1. Data Model

All new models in `backend/app/modules/strategy_lab/models.py`. Follow existing patterns from `app/models/base.py` (`Base`, `TimestampMixin`, `Mapped` + `mapped_column`).

### 1.1 StrategyVersion

```python
class StrategyVersion(Base, TimestampMixin):
    """A versioned snapshot of a strategy's parameterization.

    References an existing Strategy catalog record. Multiple versions
    per strategy form an ordered sequence (version auto-increments).
    Creating a version does NOT modify the Strategy row.
    """

    __tablename__ = "strategy_versions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    parameters: Mapped[str] = mapped_column(Text, nullable=False)   # JSON blob
    rules_hash: Mapped[str] = mapped_column(Text, nullable=False)   # SHA-256 hex
    setup_ids: Mapped[str] = mapped_column(Text, nullable=False)    # JSON list of setup IDs
    change_log: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "strategy_id", "version",
            name="uq_strategy_versions_strategy_version",
        ),
    )

    # Relationships
    strategy: Mapped["Strategy"] = relationship(back_populates="versions")
    runs: Mapped[list["Run"]] = relationship(back_populates="strategy_version")
```

**Key rules:**
- `version` auto-increments per `strategy_id` (max existing + 1, starts at 1)
- `parameters` stored as JSON text — no schema enforcement at DB level
- `rules_hash` is SHA-256 of human-readable strategy logic (not code)
- `setup_ids` is a JSON list of `setup.id` values frozen at version time
- `StrategyVersion` creation NEVER modifies the `Strategy` row
- `Strategy.active_version_id` is set manually by user, never automatically

### 1.2 Strategy modification (add one nullable FK)

```python
# On existing Strategy model (backend/app/models/strategy.py):
class Strategy(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "strategies"
    # ... existing fields ...

    active_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategy_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    versions: Mapped[list["StrategyVersion"]] = relationship(
        back_populates="strategy",
        cascade="all, delete-orphan",
    )
```

### 1.3 Experiment

```python
class Experiment(Base, TimestampMixin):
    """A hypothesis about strategy performance, grouping multiple Runs."""

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

    # Relationships
    runs: Mapped[list["Run"]] = relationship(back_populates="experiment")

    # (TimestampMixin adds created_at, updated_at)
```

**Status state machine:**
```
draft ──→ running ──→ completed
             │
             └──→ aborted
```
- `draft`: Created, no runs yet
- `running`: Set automatically when first Run starts
- `completed`: Set automatically when all Runs finish (completed or failed)
- `aborted`: Manual, immediate — existing runs remain readable

### 1.4 Run (IMMUTABLE)

```python
class Run(Base):
    """Immutable run record — NEVER updated or deleted after creation.

    Stores EVERY field needed to reproduce the run. Re-execution with
    identical config is caught by the UNIQUE constraint and returns the
    existing run. Only 'status' may transition: running → completed|failed.
    """

    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    experiment_id: Mapped[int | None] = mapped_column(
        ForeignKey("experiments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    strategy_version_id: Mapped[int] = mapped_column(
        ForeignKey("strategy_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Reproducibility (ALL mandatory)
    engine_version: Mapped[str] = mapped_column(Text, nullable=False)
    dataset_snapshot_id: Mapped[str] = mapped_column(Text, nullable=False)
    parameters: Mapped[str] = mapped_column(Text, nullable=False)       # JSON
    filters: Mapped[str] = mapped_column(Text, nullable=False)          # JSON (AnalyticsFilter)
    date_from: Mapped[str | None] = mapped_column(Text, nullable=True)  # ISO date
    date_to: Mapped[str | None] = mapped_column(Text, nullable=True)    # ISO date

    # Comparison
    baseline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Execution
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="running",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=_utcnow,
    )

    # Relationships
    experiment: Mapped["Experiment | None"] = relationship(back_populates="runs")
    strategy_version: Mapped["StrategyVersion"] = relationship(back_populates="runs")
    metrics: Mapped[list["RunMetric"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "strategy_version_id", "parameters", "filters",
            "date_from", "date_to", "engine_version",
            name="uq_runs_config_identity",
        ),
    )
```

**Immutability contract:**
| Operation | Allowed? |
|-----------|----------|
| INSERT (create) | ✅ Yes |
| SELECT (read) | ✅ Yes |
| UPDATE status only (`running`→`completed`/`failed`) | ✅ Yes (carved-out exception) |
| UPDATE any other column | ❌ No |
| DELETE | ❌ No |
| PUT/PATCH/DELETE routes | ❌ No (except PATCH status) |

**Config identity rule:** The UNIQUE constraint means identical config returns the existing Run, not a new one. To re-execute, the user must change at least one: parameters, filters, date range, or create a new strategy version.

### 1.5 RunMetric

```python
class RunMetric(Base):
    """Expensive-to-compute metric results for a Run.

    ONLY stores results that CANNOT be reconstructed from the dataset
    snapshot + AnalyticsService. Basic metrics (PF, win_rate, expectancy,
    equity curve, drawdown, sharpe) are NEVER persisted here.
    """

    __tablename__ = "run_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    ci_lower: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_upper: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    effect_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    parameters: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON — bootstrap params

    # Relationship
    run: Mapped["Run"] = relationship(back_populates="metrics")
```

**WHAT to store vs. NOT store:**

| Store in RunMetric | DO NOT Store (reconstructible from snapshot) |
|---|---|
| Bootstrap CI of difference (run A vs B) | Profit Factor |
| Permutation test p-value | Win Rate |
| Confidence level (high/medium/low) | Expectancy |
| Effect size (Cohen's d) | Avg R Multiple |
| Bootstrapped Sharpe distribution stats | Max Drawdown / Drawdown % |
| Any multi-run comparison result | Sharpe Ratio (single) |
| Any cost-to-compute aggregate (>1s) | Sortino / Calmar Ratio |
| | Payoff Ratio / Recovery Factor |
| | Equity curve points |
| | PnL by period / R Distribution |

**Rationale:** `AnalyticsService.compute_performance()` + `compute_risk()` can reconstruct all "Do Not Store" metrics from the filtered trade list. RunMetric exists ONLY for statistical results that require resampling or between-run comparison.

---

## 2. Module Structure

```
backend/app/modules/strategy_lab/
├── __init__.py                    # exports router
├── models.py                      # StrategyVersion, Experiment, Run, RunMetric
├── schemas.py                     # Pydantic request/response models
├── service.py                     # StrategyLabService
├── router.py                      # FastAPI REST endpoints
├── dependencies.py                # DI providers
├── version.py                     # Engine version capture (automatic, mandatory)
├── interfaces/
│   ├── __init__.py
│   └── comparison_engine.py       # ComparisonEngine ABC
└── implementations/
    ├── __init__.py
    └── bootstrap_comparison_engine.py  # BootstrapComparisonEngine

frontend/src/modules/strategy-lab/
├── services/
│   └── strategyLabApi.js          # API service (like analyticsApi.js)
├── hooks/
│   ├── useExperiments.js          # React Query hooks
│   ├── useRuns.js
│   ├── useComparison.js
│   └── useStrategyVersions.js
├── components/
│   ├── ExperimentList.jsx
│   ├── CreateExperimentDialog.jsx
│   ├── RunDetail.jsx
│   ├── RunMetricsTable.jsx
│   ├── ComparisonView.jsx
│   └── StrategyVersionSelector.jsx
├── pages/
│   ├── StrategyLabPage.jsx        # Experiment list
│   └── ExperimentDetailPage.jsx   # Runs + comparison
└── utils/
    └── constants.js               # Query keys, etc.
```

---

## 3. Engine Version Capture (AUTOMATIC, MANDATORY)

```python
# backend/app/modules/strategy_lab/version.py

"""Engine version capture — automatic, mandatory.

Reads the analytics engine version from installed package metadata
or git describe. Called ONCE per process lifecycle (lazy-cached).
Raises RuntimeError if version cannot be detected — Run creation
MUST fail, not silently degrade.
"""

from __future__ import annotations

import subprocess
from functools import lru_cache
from importlib.metadata import version as _pkg_version

import app  # for project root path


@lru_cache(maxsize=1)
def get_engine_version() -> str:
    """Return the analytics engine version string.

    Detection order:
    1. ``importlib.metadata.version("tip-backend")``
    2. ``git describe --always --dirty`` from project root

    Returns
    -------
    str
        Version string (e.g. "1.6.0", "v1.6.0-3-gdeadbeef-dirty").

    Raises
    ------
    RuntimeError
        If no version source is available.
    """
    # Attempt 1: installed package metadata
    try:
        return _pkg_version("tip-backend")
    except Exception:
        pass

    # Attempt 2: git describe from project root
    try:
        root = str(app.__path__[0]).rsplit("/backend/", 1)[0]  # noqa: PTH109
        result = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=root,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    raise RuntimeError(
        "Cannot determine analytics engine version. "
        "Run execution requires a detectable engine version. "
        "Ensure the package is installed or git is available."
    )
```

**Integration point** (in `service.py`):
```python
from app.modules.strategy_lab.version import get_engine_version

async def execute_run(...) -> Run:
    engine_version = get_engine_version()  # raises RuntimeError if fails
    # ... proceed with Run creation ...
```

**Behavior:**
- Called at Run creation time, in the service layer
- Cached via `@lru_cache` — detected once per process lifecycle
- If it raises `RuntimeError`, the Run is NOT created, request fails with HTTP 500
- The version string is human-readable and traceable to a specific build
- No user-facing field for engine_version in any request schema

---

## 4. ComparisonEngine Interface

```python
# backend/app/modules/strategy_lab/interfaces/comparison_engine.py

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ComparisonResult:
    """Result of comparing two runs on a single metric."""

    metric_name: str
    diff_mean: float                    # mean(values_a) - mean(values_b)
    ci_lower: float                     # 95% CI lower bound of the difference
    ci_upper: float                     # 95% CI upper bound of the difference
    p_value: float                      # Two-sided permutation test p-value
    confidence: float                   # Confidence level used (default 0.95)
    effect_size: float | None = None    # Cohen's d


class ComparisonEngine(ABC):
    """Statistical comparison between two sets of per-trade metric values.

    All methods are pure functions — no side effects, no mutable state.
    Implementations may use numpy, scipy, or pure Python.
    Domain code depends on this interface, never on concrete implementations.
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
        """Compare a single metric between two runs.

        Uses bootstrap CI of the difference of means + permutation test.

        Parameters
        ----------
        values_a : list[float]
            Per-trade metric values from run A.
        values_b : list[float]
            Per-trade metric values from run B.
        metric_name : str
            Human-readable metric label.
        n_resamples : int
            Bootstrap/permutation resample count (default 10_000).
        confidence : float
            Confidence level for CI (default 0.95).
        seed : int or None
            Random seed for reproducibility.

        Returns
        -------
        ComparisonResult
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

        Each metric is compared independently with the same values.
        Returns one ComparisonResult per metric name.
        """
```

### Implementation: BootstrapComparisonEngine

```python
# backend/app/modules/strategy_lab/implementations/bootstrap_comparison_engine.py

from __future__ import annotations

import numpy as np

from app.modules.strategy_lab.interfaces.comparison_engine import (
    ComparisonEngine,
    ComparisonResult,
)


class BootstrapComparisonEngine(ComparisonEngine):
    """Comparison engine using bootstrap CI of the difference + permutation test.

    Reuses the same statistical concepts as NumpyStatisticsEngine in
    edge discovery, but applied to the DIFFERENCE OF MEANS between
    two groups rather than a single group's mean vs zero.
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
        arr_a = np.array(values_a, dtype=np.float64)
        arr_b = np.array(values_b, dtype=np.float64)
        n_a, n_b = len(arr_a), len(arr_b)

        # Edge case: empty arrays
        if n_a == 0 or n_b == 0:
            return ComparisonResult(
                metric_name=metric_name,
                diff_mean=0.0,
                ci_lower=0.0,
                ci_upper=0.0,
                p_value=1.0,
                confidence=confidence,
                effect_size=None,
            )

        observed_diff = float(arr_a.mean() - arr_b.mean())
        rng = np.random.default_rng(seed)

        # 1. Bootstrap CI of the difference of means
        indices_a = rng.integers(0, n_a, size=(n_resamples, n_a))
        indices_b = rng.integers(0, n_b, size=(n_resamples, n_b))
        boot_diffs = arr_a[indices_a].mean(axis=1) - arr_b[indices_b].mean(axis=1)

        lower_pct = (1.0 - confidence) / 2.0 * 100
        upper_pct = (1.0 - (1.0 - confidence) / 2.0) * 100
        ci_lower = float(np.percentile(boot_diffs, lower_pct))
        ci_upper = float(np.percentile(boot_diffs, upper_pct))

        # 2. Permutation test: shuffle group labels
        combined = np.concatenate([arr_a, arr_b])
        n_total = n_a + n_b
        perm_diffs = np.empty(n_resamples)
        for i in range(n_resamples):
            rng.shuffle(combined)
            perm_a = combined[:n_a]
            perm_b = combined[n_a:]
            perm_diffs[i] = float(perm_a.mean() - perm_b.mean())

        extreme = np.abs(perm_diffs) >= np.abs(observed_diff)
        p_value = float(extreme.mean())
        p_value = max(p_value, 1.0 / (n_resamples + 1))  # Never zero

        # 3. Cohen's d effect size
        pooled_std = float(np.sqrt(
            ((n_a - 1) * np.var(arr_a, ddof=1) + (n_b - 1) * np.var(arr_b, ddof=1))
            / (n_a + n_b - 2)
        ))
        effect_size = float(observed_diff / pooled_std) if pooled_std > 0 else None

        return ComparisonResult(
            metric_name=metric_name,
            diff_mean=round(observed_diff, 6),
            ci_lower=round(ci_lower, 6),
            ci_upper=round(ci_upper, 6),
            p_value=round(p_value, 6),
            confidence=confidence,
            effect_size=round(effect_size, 4) if effect_size is not None else None,
        )

    def compare_multiple(
        self,
        values_a: list[float],
        values_b: list[float],
        metrics: list[str],
        n_resamples: int = 10_000,
        confidence: float = 0.95,
        seed: int | None = None,
    ) -> list[ComparisonResult]:
        return [
            self.compare_metric(
                values_a, values_b,
                metric_name=m,
                n_resamples=n_resamples,
                confidence=confidence,
                seed=seed,
            )
            for m in metrics
        ]
```

### DI Wiring

```python
# backend/app/modules/strategy_lab/dependencies.py

from fastapi import Depends

from app.db.dependencies import get_uow
from app.db.unit_of_work import UnitOfWork
from app.modules.strategy_lab.implementations.bootstrap_comparison_engine import (
    BootstrapComparisonEngine,
)
from app.modules.strategy_lab.interfaces.comparison_engine import ComparisonEngine
from app.modules.strategy_lab.service import StrategyLabService


async def get_comparison_engine() -> ComparisonEngine:
    """Provide a bootstrap-powered comparison engine."""
    return BootstrapComparisonEngine()


async def get_strategy_lab_service(
    uow: UnitOfWork = Depends(get_uow),
    comparison_engine: ComparisonEngine = Depends(get_comparison_engine),
) -> StrategyLabService:
    """Provide a request-scoped StrategyLabService."""
    return StrategyLabService(uow=uow, comparison_engine=comparison_engine)
```

---

## 5. Run Execution Flow

```
POST /api/strategy-lab/runs
  │
  ├─ StrategyLabService.execute_run()
  │   │
  │   ├─ 1. VALIDATE INPUTS
  │   │   ├─ strategy_version_id → exists in DB
  │   │   ├─ experiment_id → exists in DB (if provided)
  │   │   ├─ filters → valid JSON (AnalyticsFilter shape)
  │   │   ├─ parameters → valid JSON
  │   │   ├─ date_from/date_to → valid ISO dates (if provided)
  │   │   └─ baseline_run_id → exists in DB (if provided)
  │   │
  │   ├─ 2. CAPTURE ENGINE VERSION (MANDATORY)
  │   │   └─ get_engine_version()  ← raises RuntimeError if fails
  │   │       Chain breaks → HTTP 500, Run NOT created
  │   │
  │   ├─ 3. RESOLVE DATASET SNAPSHOT
  │   │   └─ Execute AnalyticsService.get_summary() with frozen filters
  │   │       → Returns list of trade IDs matching the filter
  │   │       → dataset_snapshot_id = hash of trade ID list
  │   │
  │   ├─ 4. CHECK CONFIG IDENTITY
  │   │   └─ SELECT by (strategy_version_id, parameters, filters,
  │   │                date_from, date_to, engine_version)
  │   │       → If exists, return existing Run (no new execution)
  │   │
  │   ├─ 5. CREATE RUN RECORD (status = "running")
  │   │   ├─ strategy_version_id, experiment_id (nullable)
  │   │   ├─ engine_version, dataset_snapshot_id
  │   │   ├─ parameters, filters, date_from, date_to
  │   │   ├─ baseline_run_id (nullable)
  │   │   └─ status = "running"
  │   │
  │   ├─ 6. EXECUTE ANALYTICS
  │   │   ├─ Instantiate AnalyticsFilter from stored filters JSON
  │   │   ├─ Call AnalyticsService endpoints sequentially:
  │   │   │   ├─ get_summary(filters)
  │   │   │   ├─ get_performance(filters)
  │   │   │   ├─ get_risk_metrics(filters)
  │   │   │   └─ get_equity(filters)  [for per-trade values]
  │   │   └─ Results kept in-memory (NOT persisted as RunMetric)
  │   │
  │   ├─ 7. COMPARE WITH BASELINE (if baseline_run_id exists)
  │   │   ├─ Load baseline Run metrics and trade data
  │   │   ├─ Extract per-trade metric values for both runs
  │   │   ├─ Call ComparisonEngine.compare_multiple() for each metric:
  │   │   │   ├─ "expectancy" → diff_mean, CI, p_value, effect_size
  │   │   │   ├─ "avg_r_multiple" → same
  │   │   │   ├─ "sharpe_ratio" → same
  │   │   │   └─ "profit_factor" → same
  │   │   └─ Create RunMetric for EACH comparison result
  │   │
  │   ├─ 8. UPDATE RUN STATUS → "completed"
  │   │
  │   └─ 9. RETURN Run ID + status = "completed"
```

**Error recovery:**

| Failure Point | Behavior |
|---------------|----------|
| Engine version capture fails | Run NOT created, HTTP 500 |
| Config identity match found | Return existing Run ID + current status (no error) |
| `AnalyticsService` failure | Run status → `failed`, `error_message` set, HTTP 500 |
| `ComparisonEngine` failure (during comparison) | Run status → `failed`, partial metrics rolled back |
| Partial RunMetrics stored before failure | Entire transaction rolled back (UoW pattern) |

---

## 6. API Endpoints

```
# ── Experiments ──────────────────────────────────────────────────

POST   /api/strategy-lab/experiments                          → Create experiment
  Body: { name: str, description?: str, hypothesis?: str }
  Returns 201: { id, name, description, hypothesis, status: "draft", created_at }

GET    /api/strategy-lab/experiments                           → List experiments
  Query: ?page=1&per_page=20
  Returns 200: { items: Experiment[], total: int }

GET    /api/strategy-lab/experiments/{id}                      → Get experiment detail
  Returns 200: { ...experiment, runs: Run[] }
  Returns 404: { detail: "Experiment not found" }

PATCH  /api/strategy-lab/experiments/{id}                      → Update experiment metadata
  Body: { name?: str, description?: str, hypothesis?: str }
  Returns 200: updated Experiment

POST   /api/strategy-lab/experiments/{id}/abort                → Abort experiment (status→aborted)
  Returns 200: updated Experiment with status=aborted
  Returns 422: if experiment already completed

# ── Runs ────────────────────────────────────────────────────────

POST   /api/strategy-lab/runs                                  → Execute run (create + run)
  Body: {
    strategy_version_id: int,
    experiment_id?: int,
    filters: AnalyticsFilter,
    parameters: dict,
    date_from?: date,
    date_to?: date,
    baseline_run_id?: int
  }
  Returns 201: { id, status, metrics: RunMetric[], duplicate_of?: int }

GET    /api/strategy-lab/runs                                  → List runs
  Query: ?experiment_id=1&strategy_version_id=1&page=1&per_page=20
  Returns 200: { items: Run[], total: int }

GET    /api/strategy-lab/runs/{id}                              → Get run detail
  Returns 200: { ...run, metrics: RunMetric[] }
  Returns 404

PATCH  /api/strategy-lab/runs/{id}/status                       → Update run status ONLY
  Body: { status: "completed" | "failed", error_message?: str }
  Returns 200: updated Run
  Returns 422: if status transition invalid

GET    /api/strategy-lab/runs/{id}/metrics                      → List run metrics
  Returns 200: RunMetric[]
  Returns 404

GET    /api/strategy-lab/runs/{id}/compare?baseline_id=X        → Comparison view
  Returns 200: { run_a, run_b, comparisons: ComparisonResult[] }
  Returns 404: if either run not found
  Returns 400: if runs use different strategy versions

# ── Strategy Versions ──────────────────────────────────────────

POST   /api/strategy-lab/strategies/{id}/versions               → Create strategy version
  Body: { parameters: dict, rules_hash: str, setup_ids: int[], change_log?: str }
  Returns 201: StrategyVersion
  Returns 404: if strategy not found or inactive

GET    /api/strategy-lab/strategies/{id}/versions                → List versions
  Returns 200: StrategyVersion[]

GET    /api/strategy-lab/strategies/{id}/versions/{version_id}   → Get version detail
  Returns 200: StrategyVersion
  Returns 404

PATCH  /api/strategy-lab/strategies/{id}                         → Set active version
  Body: { active_version_id: int }
  Returns 200: updated Strategy
  Returns 404: if version_id not found for this strategy
```

**Immutability enforcement by layer:**

| Layer | Enforcement |
|-------|-------------|
| DB | No UPDATE/DELETE triggers (SQLite), FK constraints prevent orphan cleanup |
| App/Repository | Only `add()` and `get()` methods — no `update()`, no `delete()` for Run |
| Router | No PUT/PATCH/DELETE routes for `/runs/{id}` (carved-out PATCH status only) |
| Alembic | IF EXISTS triggers on `runs` and `run_metrics` to prevent future modifications |

---

## 7. Service Layer

```python
# backend/app/modules/strategy_lab/service.py

class StrategyLabService:
    """Orchestration service for the Strategy Lab module.

    Handles:
    - Experiment CRUD + state machine
    - Strategy version management
    - Run execution (validate → capture version → execute → store metrics)
    - Run comparison via ComparisonEngine
    """

    def __init__(
        self,
        uow: UnitOfWork,
        comparison_engine: ComparisonEngine,
    ) -> None:
        self.uow = uow
        self.comparison_engine = comparison_engine

    # ── Experiments ──────────────────────────────────────────────────────

    async def create_experiment(self, data: ExperimentCreate) -> Experiment: ...
    async def list_experiments(self, page: int, per_page: int) -> tuple[list[Experiment], int]: ...
    async def get_experiment(self, id: int) -> Experiment | None: ...
    async def update_experiment(self, id: int, data: ExperimentUpdate) -> Experiment: ...
    async def abort_experiment(self, id: int) -> Experiment: ...

    # ── Strategy Versions ────────────────────────────────────────────────

    async def create_version(
        self, strategy_id: int, data: StrategyVersionCreate
    ) -> StrategyVersion: ...
    async def list_versions(self, strategy_id: int) -> list[StrategyVersion]: ...
    async def get_version(self, strategy_id: int, version_id: int) -> StrategyVersion: ...
    async def set_active_version(
        self, strategy_id: int, active_version_id: int
    ) -> Strategy: ...

    # ── Runs ─────────────────────────────────────────────────────────────

    async def execute_run(self, data: RunCreate) -> Run:
        """Full run execution pipeline.

        1. Validate all FK references
        2. Capture engine version (MANDATORY — raises if fails)
        3. Resolve dataset snapshot ID
        4. Check config identity (UNIQUE constraint)
        5. Create Run record (status=running)
        6. Execute AnalyticsService with frozen filters
        7. Compare with baseline if baseline_run_id set
        8. Store expensive RunMetrics
        9. Update Run status=completed
        10. Return Run
        """

    async def list_runs(
        self, experiment_id: int | None, page: int, per_page: int
    ) -> tuple[list[Run], int]: ...

    async def get_run(self, id: int) -> Run | None: ...

    async def update_run_status(
        self, id: int, status: str, error_message: str | None = None
    ) -> Run: ...

    async def compare_runs(
        self, run_id: int, baseline_id: int
    ) -> ComparisonResponse: ...
```

**Key design notes:**
- `execute_run()` is synchronous — metrics computation is fast (in-memory numpy/pandas), no blocking I/O after trade fetch
- `AnalyticsService` is instantiated from the UoW (same transaction)
- The `ConfigIdentity` UNIQUE constraint is checked before INSERT — if match found, return existing Run
- RunMetrics are saved inside the same UoW transaction; failure before commit rolls back everything

---

## 8. Repository Layer

Extend `UnitOfWork` with lazy-init repositories for the new models:

```python
# backend/app/db/unit_of_work.py (additions)

class UnitOfWork:
    # ... existing repos ...

    @property
    def strategy_versions(self) -> "SqlAlchemyRepository[StrategyVersion]":
        if self._strategy_versions is None:
            from app.modules.shared.base import SqlAlchemyRepository
            from app.modules.strategy_lab.models import StrategyVersion
            self._strategy_versions = SqlAlchemyRepository(
                self._session, StrategyVersion
            )
        return self._strategy_versions

    @property
    def experiments(self) -> "SqlAlchemyRepository[Experiment]":
        if self._experiments is None:
            from app.modules.shared.base import SqlAlchemyRepository
            from app.modules.strategy_lab.models import Experiment
            self._experiments = SqlAlchemyRepository(self._session, Experiment)
        return self._experiments

    @property
    def runs(self) -> "RunRepository":
        """Custom RunRepository that enforces immutability."""
        if self._runs is None:
            from app.modules.strategy_lab.repository import RunRepository
            self._runs = RunRepository(self._session)
        return self._runs

    @property
    def run_metrics(self) -> "SqlAlchemyRepository[RunMetric]":
        if self._run_metrics is None:
            from app.modules.shared.base import SqlAlchemyRepository
            from app.modules.strategy_lab.models import RunMetric
            self._run_metrics = SqlAlchemyRepository(
                self._session, RunMetric
            )
        return self._run_metrics
```

**RunRepository** (custom — extends SqlAlchemyRepository with immutability):

```python
# backend/app/modules/strategy_lab/repository.py

from app.modules.shared.base import SqlAlchemyRepository
from app.modules.strategy_lab.models import Run


class RunRepository(SqlAlchemyRepository[Run]):
    """Run repository with immutability enforcement.

    Overrides 'update' and 'delete' to raise — Runs are
    append-only. Only status may change via dedicated method.
    """

    async def update(self, entity: Run) -> Run:
        raise NotImplementedError("Run is immutable — use update_status()")

    async def delete(self, entity: Run) -> None:
        raise NotImplementedError("Run is immutable — cannot delete")

    async def update_status(
        self, run_id: int, new_status: str, error_message: str | None = None
    ) -> Run:
        """Carved-out status update for runs.

        Only allowed transitions: running → completed, running → failed.
        """
        run = await self.get(run_id)
        if run is None:
            raise NotFoundError(f"Run {run_id} not found")

        _valid_transitions = {
            "running": ["completed", "failed"],
        }
        allowed = _valid_transitions.get(run.status, [])
        if new_status not in allowed:
            raise BusinessRuleError(
                f"Cannot transition run from '{run.status}' to '{new_status}'",
                field="status",
            )

        run.status = new_status
        if error_message:
            run.error_message = error_message
        return await super().update(run)  # type: ignore[override]
```

---

## 9. Repositories for Edge Discovery Repos (SQLite direct)

For experiment, strategy versions, runs, and run metrics — we use the existing `SqlAlchemyRepository` pattern through the `UnitOfWork`. The edge discovery module uses a direct SQLite repository (`SqliteEdgeRepository`) with raw queries — we do NOT reuse that pattern. The strategy lab uses SQLAlchemy ORM through the UoW, consistent with all other modules.

---

## 10. Frontend Architecture

### 10.1 API Service

```javascript
// frontend/src/modules/strategy-lab/services/strategyLabApi.js
import { api } from '../../../shared/lib/api';

export const strategyLabApi = {
  // ── Experiments ──────────────────────────────────────────────
  listExperiments: (params) =>
    api.get('/strategy-lab/experiments', { params }),

  getExperiment: (id) =>
    api.get(`/strategy-lab/experiments/${id}`),

  createExperiment: (body) =>
    api.post('/strategy-lab/experiments', body),

  updateExperiment: (id, body) =>
    api.patch(`/strategy-lab/experiments/${id}`, body),

  abortExperiment: (id) =>
    api.post(`/strategy-lab/experiments/${id}/abort`),

  // ── Runs ─────────────────────────────────────────────────────
  listRuns: (params) =>
    api.get('/strategy-lab/runs', { params }),

  getRun: (id) =>
    api.get(`/strategy-lab/runs/${id}`),

  executeRun: (body) =>
    api.post('/strategy-lab/runs', body),

  compareRuns: (runId, baselineId) =>
    api.get(`/strategy-lab/runs/${runId}/compare?baseline_id=${baselineId}`),

  // ── Strategy Versions ────────────────────────────────────────
  listVersions: (strategyId) =>
    api.get(`/strategy-lab/strategies/${strategyId}/versions`),

  createVersion: (strategyId, body) =>
    api.post(`/strategy-lab/strategies/${strategyId}/versions`, body),

  setActiveVersion: (strategyId, activeVersionId) =>
    api.patch(`/strategy-lab/strategies/${strategyId}`, { active_version_id: activeVersionId }),
};
```

### 10.2 React Query Hooks Pattern

```javascript
// frontend/src/modules/strategy-lab/hooks/useExperiments.js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { strategyLabApi } from '../services/strategyLabApi';
import { QUERY_KEYS } from '../utils/constants';

export function useExperiments(page = 1) {
  return useQuery({
    queryKey: QUERY_KEYS.experiments.list(page),
    queryFn: () => strategyLabApi.listExperiments({ page }),
  });
}

export function useExperiment(id) {
  return useQuery({
    queryKey: QUERY_KEYS.experiments.detail(id),
    queryFn: () => strategyLabApi.getExperiment(id),
    enabled: !!id,
  });
}

export function useCreateExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: strategyLabApi.createExperiment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEYS.experiments._def });
    },
  });
}
```

### 10.3 Component States

Every data-dependent component must handle 4 states:

| State | UI |
|-------|-----|
| **Loading** | Skeleton rows (list) / Spinner (detail) |
| **Error** | Alert with message + Retry button |
| **Empty** | Empty illustration with CTA |
| **Success** | Data rendered with metrics |

### 10.4 Page Structure

| Route | Page Component | Key Components |
|-------|---------------|----------------|
| `/strategy-lab` | `StrategyLabPage` | `ExperimentList`, `CreateExperimentDialog` |
| `/strategy-lab/experiments/{id}` | `ExperimentDetailPage` | `RunDetail`, `RunMetricsTable`, strategy version selector |
| `/strategy-lab/runs/{id}` | `RunDetailPage` | `RunMetricsTable`, reproducibility info card |
| `/strategy-lab/runs/{id}/compare?baseline_id=X` | `ComparisonPage` | `ComparisonView` (two-column side-by-side) |

### 10.5 ComparisonView Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Run A (#123)                    │  Run B (#456)              │
│  version: 2                      │  version: 2                │
│  trades: 245                     │  trades: 312               │
├──────────────────────────────────┼────────────────────────────┤
│  Expectancy: 1.84                │  Expectancy: 0.92          │
│  Win Rate: 58.3%                 │  Win Rate: 51.2%           │
│  Profit Factor: 2.1              │  Profit Factor: 1.4        │
│  Sharpe: 1.45                    │  Sharpe: 0.78              │
├──────────────────────────────────┼────────────────────────────┤
│  ── Comparison ──                │                            │
│  Metric          │ Delta  │ CI         │ p      │ ES │
│  Expectancy      │ +0.92  │ [0.4, 1.5] │ 0.002  │ 0.8 │
│  Sharpe          │ +0.67  │ [0.2, 1.1] │ 0.008  │ 0.6 │
│  Profit Factor   │ +0.70  │ [-0.1,1.4] │ 0.054  │ 0.3 │
└──────────────────────────────────────────────────────────────┘
```

---

## 11. Migration Plan

```python
# alembic/versions/XXXX_strategy_lab_v1.py

"""Strategy Lab v1 — Experiment, Run, StrategyVersion, RunMetric tables.

Revision ID: XXXX
Revises: <previous_revision>
Create Date: 2026-07-12
"""

def upgrade():
    # 1. Create strategy_versions
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
        sa.ForeignKeyConstraint(
            ["strategy_id"], ["strategies.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "strategy_id", "version",
            name="uq_strategy_versions_strategy_version",
        ),
    )
    with op.batch_alter_table("strategy_versions") as batch_op:
        batch_op.create_index("ix_strategy_versions_strategy_id", ["strategy_id"])

    # 2. Add active_version_id to strategies
    with op.batch_alter_table("strategies") as batch_op:
        batch_op.add_column(
            sa.Column("active_version_id", sa.Integer(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_strategies_active_version_id_strategy_versions",
            "strategy_versions", ["active_version_id"], ["id"],
            ondelete="SET NULL",
        )

    # 3. Create experiments
    op.create_table("experiments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("hypothesis", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=True),
    )

    # 4. Create runs
    op.create_table("runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("experiment_id", sa.Integer(), nullable=True),
        sa.Column("strategy_version_id", sa.Integer(), nullable=False),
        sa.Column("engine_version", sa.Text(), nullable=False),
        sa.Column("dataset_snapshot_id", sa.Text(), nullable=False),
        sa.Column("parameters", sa.Text(), nullable=False),
        sa.Column("filters", sa.Text(), nullable=False),
        sa.Column("date_from", sa.Text(), nullable=True),
        sa.Column("date_to", sa.Text(), nullable=True),
        sa.Column("baseline_run_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="running"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["experiment_id"], ["experiments.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["strategy_version_id"], ["strategy_versions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["baseline_run_id"], ["runs.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "strategy_version_id", "parameters", "filters",
            "date_from", "date_to", "engine_version",
            name="uq_runs_config_identity",
        ),
    )
    with op.batch_alter_table("runs") as batch_op:
        batch_op.create_index("ix_runs_experiment_id", ["experiment_id"])
        batch_op.create_index("ix_runs_strategy_version_id", ["strategy_version_id"])

    # 5. Create run_metrics
    op.create_table("run_metrics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("ci_lower", sa.Float(), nullable=True),
        sa.Column("ci_upper", sa.Float(), nullable=True),
        sa.Column("p_value", sa.Float(), nullable=True),
        sa.Column("effect_size", sa.Float(), nullable=True),
        sa.Column("parameters", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["run_id"], ["runs.id"],
            ondelete="CASCADE",
        ),
    )
    with op.batch_alter_table("run_metrics") as batch_op:
        batch_op.create_index("ix_run_metrics_run_id", ["run_id"])

    # 6. Immutability enforcement triggers
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_runs_no_update
        BEFORE UPDATE ON runs
        BEGIN
            SELECT CASE
                WHEN NEW.status = OLD.status
                     OR (OLD.status = 'running' AND NEW.status IN ('completed', 'failed'))
                THEN NULL
                ELSE RAISE(ABORT, 'Run is immutable — only status can change')
            END;
        END;
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_runs_no_delete
        BEFORE DELETE ON runs
        BEGIN
            SELECT RAISE(ABORT, 'Run is immutable — cannot delete');
        END;
    """)
    op.execute("""
        CREATE TRIGGER IF NOT EXISTS trg_run_metrics_no_delete
        BEFORE DELETE ON run_metrics
        BEGIN
            SELECT RAISE(ABORT, 'RunMetric is immutable — cannot delete');
        END;
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS trg_runs_no_update")
    op.execute("DROP TRIGGER IF EXISTS trg_runs_no_delete")
    op.execute("DROP TRIGGER IF EXISTS trg_run_metrics_no_delete")

    op.drop_table("run_metrics")
    op.drop_table("runs")
    op.drop_table("experiments")

    with op.batch_alter_table("strategies") as batch_op:
        batch_op.drop_constraint(
            "fk_strategies_active_version_id_strategy_versions",
            type_="foreignkey",
        )
        batch_op.drop_column("active_version_id")

    op.drop_table("strategy_versions")
```

---

## 12. Testing Strategy

### 12.1 Unit Tests

| Test File | What It Tests |
|-----------|---------------|
| `tests/modules/strategy_lab/test_models.py` | Model creation, FK constraints, UNIQUE constraints, default values |
| `tests/modules/strategy_lab/test_version.py` | Engine version capture: happy path, git fallback, cache behavior, failure mode |
| `tests/modules/strategy_lab/test_comparison_engine.py` | `compare_metric()`: two different runs, identical runs, empty values, single values, seeding reproducibility |
| `tests/modules/strategy_lab/test_repository.py` | RunRepository: immutability enforcement (update/delete raise), status transitions, config identity lookup |
| `tests/modules/strategy_lab/test_service.py` | `execute_run()`: full pipeline, duplicate config return existing, version failure, analytics failure |
| `tests/modules/strategy_lab/test_router.py` | All endpoints: happy path, 404, 422, 500, immutability enforcement at API level |
| `tests/modules/strategy_lab/test_experiment_state_machine.py` | Experiment status transitions: valid (draft→running→completed, running→aborted), invalid (completed→draft, aborted→running) |
| `tests/modules/strategy_lab/test_strategy_version.py` | Version auto-increment per strategy, parallel counters per strategy, validation |

### 12.2 Integration Tests

| Test File | What It Tests |
|-----------|---------------|
| `tests/modules/strategy_lab/test_execution_flow.py` | Full run execution end-to-end: create strategy version → create experiment → execute run → verify metrics |
| `tests/modules/strategy_lab/test_comparison_flow.py` | Two runs → compare → verify RunMetrics stored with CI and p-value |
| `tests/modules/strategy_lab/test_config_identity.py` | Same config twice → same Run returned |
| `tests/modules/strategy_lab/test_migration.py` | Migration up/down, verify all triggers fire |

### 12.3 Frontend Tests

| Test File | What It Tests |
|-----------|---------------|
| `__tests__/ExperimentList.test.jsx` | Rendering: populated, empty, loading, error states |
| `__tests__/CreateExperimentDialog.test.jsx` | Form validation, submission, success/error handling |
| `__tests__/RunDetail.test.jsx` | Metrics table rendering, reproducibility card, status badge |
| `__tests__/ComparisonView.test.jsx` | Two-column layout, delta calculation, significance highlighting, "not comparable" state |

### 12.4 Key Test Scenarios

| Scenario | Verification |
|----------|-------------|
| Run with baseline | RunMetrics contain `comparison.expectancy`, `comparison.sharpe` entries with non-null CI and p-value |
| Run without baseline | RunMetrics is empty (no expensive metrics to store) |
| Config identity | Same POST × 2 → same Run ID returned on second call |
| Engine version failure | POST returns 500, no Run created |
| Immutability enforcement | Any attempt to update non-status fields → 422/error |
| Version auto-increment | Strategy 1: v1, v2, v3; Strategy 2: v1 (independent) |

---

## 13. File Impact List

### New Files (Created)

```
backend/app/modules/strategy_lab/__init__.py
backend/app/modules/strategy_lab/models.py
backend/app/modules/strategy_lab/schemas.py
backend/app/modules/strategy_lab/service.py
backend/app/modules/strategy_lab/router.py
backend/app/modules/strategy_lab/dependencies.py
backend/app/modules/strategy_lab/version.py
backend/app/modules/strategy_lab/repository.py
backend/app/modules/strategy_lab/interfaces/__init__.py
backend/app/modules/strategy_lab/interfaces/comparison_engine.py
backend/app/modules/strategy_lab/implementations/__init__.py
backend/app/modules/strategy_lab/implementations/bootstrap_comparison_engine.py

alembic/versions/XXXX_strategy_lab_v1.py

frontend/src/modules/strategy-lab/services/strategyLabApi.js
frontend/src/modules/strategy-lab/hooks/useExperiments.js
frontend/src/modules/strategy-lab/hooks/useRuns.js
frontend/src/modules/strategy-lab/hooks/useComparison.js
frontend/src/modules/strategy-lab/hooks/useStrategyVersions.js
frontend/src/modules/strategy-lab/components/ExperimentList.jsx
frontend/src/modules/strategy-lab/components/CreateExperimentDialog.jsx
frontend/src/modules/strategy-lab/components/RunDetail.jsx
frontend/src/modules/strategy-lab/components/RunMetricsTable.jsx
frontend/src/modules/strategy-lab/components/ComparisonView.jsx
frontend/src/modules/strategy-lab/components/StrategyVersionSelector.jsx
frontend/src/modules/strategy-lab/pages/StrategyLabPage.jsx
frontend/src/modules/strategy-lab/pages/ExperimentDetailPage.jsx
frontend/src/modules/strategy-lab/utils/constants.js
```

### Modified Files

```
backend/app/models/strategy.py           # Add active_version_id FK + relationship
backend/app/db/unit_of_work.py           # Add 4 lazy-init repository properties
backend/app/db/dependencies.py           # Add get_strategy_lab_service()
```

### Test Files (Created)

```
backend/tests/modules/strategy_lab/test_models.py
backend/tests/modules/strategy_lab/test_version.py
backend/tests/modules/strategy_lab/test_comparison_engine.py
backend/tests/modules/strategy_lab/test_repository.py
backend/tests/modules/strategy_lab/test_service.py
backend/tests/modules/strategy_lab/test_router.py
backend/tests/modules/strategy_lab/test_experiment_state_machine.py
backend/tests/modules/strategy_lab/test_strategy_version.py
backend/tests/modules/strategy_lab/test_execution_flow.py
backend/tests/modules/strategy_lab/test_comparison_flow.py
backend/tests/modules/strategy_lab/test_config_identity.py
backend/tests/modules/strategy_lab/test_migration.py

frontend/src/modules/strategy-lab/components/__tests__/ExperimentList.test.jsx
frontend/src/modules/strategy-lab/components/__tests__/CreateExperimentDialog.test.jsx
frontend/src/modules/strategy-lab/components/__tests__/RunDetail.test.jsx
frontend/src/modules/strategy-lab/components/__tests__/ComparisonView.test.jsx
```

---

## 14. PR Slicing (Stacked to Main)

| PR | Focus | Files | Est. LOC | Dependencies |
|----|-------|-------|----------|--------------|
| **#1 — Data Layer** | Models, migration, strategy.py modification, `__init__.py` exports, UoW repos | 8 new + 2 modified | ~400 | None |
| **#2 — Engine** | ComparisonEngine interface + BootstrapComparisonEngine, version.py, repository.py with immutability | 6 new | ~500 | #1 (needs models) |
| **#3 — API** | Router, schemas, service, dependencies, DI wiring, integration tests | 6 new + 1 modified (dependencies.py) | ~350 | #2 (needs service + engine) |
| **#4 — Frontend** | Pages, components, hooks, API service, tests | 15 new | ~450 | #3 (needs API) |

**Merge strategy:** Each PR is stacked on the previous one. Each PR independently passes tests after merge.

---

## 15. ADR-008 Traceability

| Decision | Source | Section |
|----------|--------|---------|
| StrategyVersion FK to `strategies.id` | User adjustment #1 | §1.1 |
| Run stores all reproducibility fields | User adjustment #2 | §1.4 |
| RunMetric only stores expensive results | User adjustment #3 | §1.5 |
| Engine version mandatory + automatic | User adjustment #4 | §3 |
| ComparisonEngine behind ABC interface | User adjustment #5 | §4 |
| Run is immutable (no UPDATE/DELETE) | User adjustment #6 | §1.4, §8, §11 |
| StrategyVersion auto-increments per strategy | Spec R1 | §1.1 |
| Experiment status state machine | Spec R2 | §1.3 |
| Config identity UNIQUE constraint | Spec R3 | §1.4 |
| Synchronous execution (metrics are fast, no I/O wait) | Design decision | §5 |
| Same SQLite DB (offline-first) | Architecture constraint | §11 |
| Bootstrap CI on difference of means | Edge discovery pattern (#5) | §4 |
| `SqlAlchemyRepository` pattern | Existing UoW pattern | §8 |
| Frontend React Query pattern | Existing analytics module | §10 |

---

## 16. Constraints Satisfied

| Constraint | How |
|------------|-----|
| **Offline-first** | All new tables in existing `trading_journal.db` (SQLite), no external services |
| **No journal modifications** | Only `Strategy` gets a nullable FK — no changes to Trade, Analytics, or Edge Discovery models |
| **No generative AI** | All comparison logic is classical statistics (bootstrap CI + permutation test) |
| **No duplicating analytics** | RunMetric stores ONLY results the AnalyticsService cannot produce from a single trade list |
| **ADR-008 traceability** | Every design decision links back to the source (user adjustment, spec requirement, or exploration finding) |
