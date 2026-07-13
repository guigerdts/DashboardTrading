# Exploration: Strategy Lab (v1.6.0)

> **SDD Phase**: Explore — codebase investigation for 6 discovery questions.
> **Current Version**: v1.5.0 (AI Insights just merged). Next: v1.6.0 Strategy Lab.
> **Started**: 2026-07-12

---

## 1. Strategy Version — What Does It Represent?

### Current State

Strategies are **simple catalog entities** stored in the `strategies` table:

- **Model**: `backend/app/models/strategy.py` — `Strategy(Base, TimestampMixin, SoftDeleteMixin)`
  - Columns: `id` (PK), `name` (unique), `description`, `created_at`, `updated_at`, `is_active`
  - **No versioning mechanism exists**. A strategy is just a name + optional description.
  - **No parameters column**. No rules column. No version number.
- **Junction table**: `strategy_setups` — M:N between Strategy and Setup.
- **Usage in trades**: `trade.strategy_id` is an optional FK → `strategies(id)` with `ON DELETE SET NULL`.
- **Repository**: `CatalogRepository(Strategy)` via `UnitOfWork.strategies` — generic CRUD (create, update, archive, list_active).
- **API**: `GET/POST/PUT /api/catalogs/strategies` — generic catalog REST.

### Discovery: What Makes a Strategy Version?

A strategy version **must capture everything that determines trade behavior**:

```
Strategy Version = rules (logic) + parameters (configuration)
```

| Component | Today | Future |
|-----------|-------|--------|
| **Rules** | No storage | Strategy code snapshot or rule DSL |
| **Parameters** | No storage | JSON blob or normalized columns |
| **Setup associations** | M:N via `strategy_setups` | Versioned association |
| **Risk profile** | `risk_profiles` table exists but not wired | Versioned risk config |

### Recommendation

Model a strategy version as an **immutable snapshot** of the strategy's rules + parameters at a point in time. Use a `StrategyVersion` entity with:

```
StrategyVersion:
  - id: PK
  - strategy_id: FK → strategies(id)  [the base catalog entity, never modified]
  - version: int (monotonic, per strategy)
  - name: str (human label, e.g. "v1.0", "mean-reversion-v2")
  - description: str | None
  - parameters: JSON blob (all tunable params)
  - rules_hash: str (SHA-256 of rules definition — for dedup/diff)
  - setup_ids: JSON list (which setups this version uses)
  - change_log: str | None (what changed from previous version)
  - created_at: str (timestamp)
  - is_active: bool (soft-delete)
```

**Constraint**: Do **not** modify the existing `Strategy` or `Trade` models. The trade journal remains untouched. `StrategyVersion` is a pure Strategy Lab entity.

---

## 2. Entities: Experiment, Run, Baseline

### Current Data Model

- **Trade**: `backend/app/models/trade.py` — 25+ columns, wide table with 9 FKs. Canonical SSOT.
- **Strategy**: `backend/app/models/strategy.py` — catalog entity. Name + description only.
- **Setup**: `backend/app/models/strategy.py` — catalog entity. Name + description only.
- **Tag**: `backend/app/models/tag.py` — category + color support.
- **Mistake**: `backend/app/models/mistake.py` — catalog entity.
- **Asset**: `backend/app/models/asset.py` — symbol + market_id.
- **Account**: `backend/app/models/account.py` — name, broker, currency, status.
- **RiskProfile**: `backend/app/alembic/versions/970bf55b0d74.py` — has `name`, `strategy_id`, `max_risk_per_trade`, `position_sizing_method`, `max_daily_loss`, `max_concurrent_trades`. Table exists, but the `risk_management` module is **still scaffold** with no implementation.

### Nonexistent (all new)

**Experiment**, **Run**, and **Baseline** do not exist in any form — not in models, not in modules, not in schemas.

### Proposed Entity Relationships

```
Experiment ──1:N──> Run ──N:1──> StrategyVersion
                        │
                        └──> Baseline (reference to a specific Run or StrategyVersion)
```

#### Experiment = a hypothesis to test

```
Experiment:
  - id: PK
  - name: str (e.g. "Momentum vs Mean Reversion on EUR/USD")
  - description: str | None
  - hypothesis: str | None (what are we testing?)
  - status: "draft" | "running" | "completed" | "archived"
  - created_at: str
  - updated_at: str | None
```

An Experiment groups related Runs. It's the container for a scientific question.

#### Run = a single execution of an experiment (immutable)

```
Run:
  - id: PK
  - experiment_id: FK → experiments(id)
  - strategy_version_id: FK → strategy_versions(id)  [what was tested]
  - label: str (e.g. "Momentum - EUR/USD - 2024")
  - status: "pending" | "running" | "completed" | "failed"
  - date_from: str (inclusive)
  - date_to: str (exclusive)
  - filter_params: JSON (account_id, asset_id, market_id, etc.)
  - analytics_params: JSON (window_size for rolling, etc.)
  - analytics_engine_version: str (git commit hash for reproducibility)
  - run_duration_ms: int | None
  - error_message: str | None
  - created_at: str
  - completed_at: str | None
```

A Run is **immutable once completed**. It stores all context needed to reproduce the calculation.

#### RunMetric = captured analytics for a Run

```
RunMetric:
  - id: PK
  - run_id: FK → runs(id)
  - metric_name: str (e.g. "net_pnl", "win_rate", "sharpe_ratio")
  - metric_value: float
  - metric_type: "performance" | "risk" | "edge"
```

Stores the **results** of calling the existing `AnalyticsService` with the run's filter params. This captures the "what happened" without duplicating analytics logic.

#### Baseline = a reference strategy version for comparison

A baseline is **not a separate entity** — it's a reference pattern:

- Option A: A `Baseline` entity links to a `StrategyVersion` and is associated with an `Experiment` (or is global).
- Option B: A Run has an optional `baseline_run_id` FK to another Run.
- Option C: An Experiment has a `baseline_strategy_version_id`.

**Recommendation**: Option B — `Run.baseline_run_id`. Every run can optionally reference a baseline run. This is the most flexible: you can compare Run A against Run B regardless of which strategy version they use.

### Journal Invariant

None of these entities touch `trades`, `strategies`, `accounts`, `assets`, `tags`, or any journal table. The trade journal is **read-only** from Strategy Lab — queried via `AnalyticsFilter` time ranges.

---

## 3. Parameter and Rule Versioning

### Current State

**No parameter storage exists anywhere in the codebase.** There is:
- No `parameters` column on `Strategy`
- No `rules` table or column
- No `config` blob on trades or strategies
- No DSL or rule definition mechanism

The closest existing pattern is:

1. **Edge Discovery params** (in `EdgeGenerateRequest` / `EdgeDiscoveryEngine.generate()`): `min_observations`, `bootstrap_resamples`, `fdr_alpha`, `stability_threshold`, `seed`. Stored as JSON in `edge_snapshots.params`.
2. **AnalyticsFilter**: `account_id`, `asset_id`, `market_id`, `date_from`, `date_to`, `window_size`. All optional, all simple types.
3. **RiskProfile**: Has `max_risk_per_trade`, `position_sizing_method`, `max_daily_loss`, `max_concurrent_trades` — but only as columns, not as a snapshot.

### Recommendation: Parameter Snapshot as JSON Blob

Store parameters as a **JSON blob** on `StrategyVersion`. Rationale:

| Approach | Pros | Cons |
|----------|------|------|
| JSON blob on StrategyVersion | Simple, schema-less, easy to diff | No DB-level validation, harder to query individual params |
| Normalized columns per param type | DB validation, queryable | Schema churn, every strategy has different params |
| Hybrid: JSON blob + indexed computed columns | Best of both for queryable subset | Higher complexity |

**Recommendation**: JSON blob. Strategy parameters are inherently schema-less (each strategy type needs different parameters). Use Pydantic models per strategy type at the application layer for validation.

Example `parameters` blob:

```json
{
  "entry_conditions": {
    "rsi_period": 14,
    "rsi_oversold": 30,
    "rsi_overbought": 70
  },
  "exit_conditions": {
    "take_profit_atr_multiple": 2.0,
    "stop_loss_atr_multiple": 1.5
  },
  "position_sizing": {
    "method": "fixed_fractional",
    "risk_per_trade_pct": 1.0
  },
  "filters": {
    "min_volume": 100000,
    "max_spread": 2.0
  }
}
```

### Rule Versioning

For Phase 1 (MVP), treat "rules" as part of the strategy **name/description** — the human-readable description captures what the strategy does. The `rules_hash` field on `StrategyVersion` can fingerprint the strategy logic for dedup.

For Phase 2+, a `Rule` entity can be introduced:

```
Rule:
  - id: PK
  - strategy_version_id: FK → strategy_versions(id)
  - rule_type: "entry" | "exit" | "filter" | "sizing"
  - condition: str (human-readable or DSL)
  - created_at: str
```

But this is **out of scope** for the initial Strategy Lab.

---

## 4. Walk-Forward Execution

### Current State

**No walk-forward or time-series split capability exists.** Searching the codebase:

- **AnalyticsFilter**: Has `date_from` / `date_to` — supports arbitrary time-range filtering.
- **AnalyticsService**: `get_summary()`, `get_equity()`, `get_performance()`, `get_risk_metrics()` all accept `AnalyticsFilter` and pass `**filters.to_filter_kwargs()` to `self.uow.trades.list_closed()`.
- **TradeRepository.list_closed()**: Accepts `date_from`/`date_to` and filters on `exit_datetime`. This is the **foundation** for walk-forward — we can query any time window.
- **Edge Discovery**: Computes split-half stability (chronological split by exit_datetime). This is a **simple form of cross-validation** but not walk-forward.

### How Walk-Forward Would Work

```
Training window ────────────┐
(compute params/edge)       │
                            ├──> Test window ──> metrics
                            │    (evaluate)
                            │
Next training window ───────┤
                            ├──> Next test window ──> metrics
                            │
...                          ...
```

**Implementation approach**:

1. The Run stores `date_from` and `date_to` — these define the test window.
2. Walk-forward is an **execution strategy**, not a new entity. A "WalkForwardRun" would contain N sub-runs (one per window pair).
3. Sub-runs are not new entities — they're just `Run` records with a `parent_run_id` FK and a `window_index` field:

```
Run.walk_forward:
  - parent_run_id: int | None (FK → runs(id))
  - window_index: int | None
  - training_date_from: str | None
  - training_date_to: str | None
```

4. The walk-forward **orchestrator** calls `AnalyticsService` for each window pair, creating one `Run` + `RunMetric` records per window. This is new code but reuses the existing analytics engine.

### Reusing Analytics Engine

```python
# Pseudo-code — pure new code in Strategy Lab, no analytics modification
for window in walk_forward_windows:
    # Training window: compute optimal params (not in scope for MVP)
    # Test window: evaluate performance
    test_filter = AnalyticsFilter(
        date_from=window.test_date_from,
        date_to=window.test_date_to,
        account_id=experiment.account_id,
        asset_id=experiment.asset_id,
    )
    result = await analytics_service.get_summary(test_filter)
    # Store result as RunMetrics
```

### Storage: Nested Pattern

Walk-forward results follow the **Same Snapshot Pattern** as Edge Discovery:

- `Run` (parent) → stores walk-forward config (total windows, window_size, step_size)
- `Run` (children) → one per window, linked via `parent_run_id`
- `RunMetric` → per window metrics

---

## 5. Statistical Comparison

### Current State

**No strategy comparison capability exists.** The codebase has:

#### Existing Statistical Tools (in Edge Discovery)

| Tool | Location | Can Reuse? |
|------|----------|------------|
| Bootstrap CI (`compute_bootstrap_ci`) | `edge_discovery/implementations/numpy_statistics_engine.py` | **Yes** — pure function, takes `list[float]` |
| Bootstrap p-value (`compute_p_value`) | Same | **Yes** — two-sided test against null=0 |
| Split-half stability | `engine/stability.py` | Partial — need cross-strategy stability |
| FDR correction (Benjamini-Hochberg) | `engine/fdr.py` | Yes — for multiple comparison correction |
| Confidence level gating | `engine/statistical_gate.py` | Partial — similar logic for comparison gates |
| Composite edge score | `engine/scorer.py` | No — too tied to edge discovery domain |

#### Analytics Comparison (existing)

`AnalyticsService.compare_periods()`: Compares two date ranges by running `compute_performance()` on each and computing delta/delta_percent. This is **descriptive comparison** — no statistical significance.

### What's Needed

To determine "Strategy A > Strategy B", we need **statistical hypothesis testing**:

| Test | Purpose | Existing? |
|------|---------|-----------|
| Bootstrap CI of difference in means | Does A outperform B with 95% confidence? | CI exists, but not for difference |
| Permutation test (A vs B) | Is the observed difference due to chance? | No |
| Welch's t-test | Parametric alternative | No |
| Paired bootstrap (same-period comparison) | When strategies traded same assets/periods | No |
| Deflated Sharpe Ratio | Accounts for multiple testing in strategy search | No |

### Recommendation: Bootstrap-Based Comparison Engine

Create a lightweight `StrategyComparisonEngine` that:

```python
class StrategyComparisonEngine:
    """Pure statistical comparison between two strategy versions.
    
    Reuses NumpyStatisticsEngine for bootstrap computations.
    Does not duplicate any analytics or edge discovery logic.
    """
    
    async def compare(
        self,
        trades_a: list[Trade],
        trades_b: list[Trade],
        n_resamples: int = 10_000,
        seed: int | None = None,
    ) -> ComparisonResult:
        # 1. Compute performance metrics for each group (calls compute_performance)
        # 2. Bootstrap CI of the difference in means
        # 3. Permutation test for significance
        # 4. Report: is A better than B? With what confidence?
```

This is **new code** but must:
- Import `compute_performance` from analytics calculators (reuse, not duplicate)
- Import `NumpyStatisticsEngine` methods (reuse, not duplicate)
- NOT modify any existing analytics or edge discovery code

### Key Invariant

> AI Insights only interprets existing results; never calculates metrics.

Statistical comparison is a **deterministic calculation engine** (like Analytics and Edge Discovery), so it belongs alongside them, not in AI Insights.

---

## 6. Reproducibility — Minimum Valuable Data

### What's Needed to Reproduce a Run

| Component | Storage | Current State | Needed? |
|-----------|---------|---------------|---------|
| Dataset snapshot (trade IDs) | IDs only (trades are immutable journal) | Trade IDs available via query | **Yes** — store trade_ids on Run (lightweight pointer) |
| Strategy version ID | FK → strategy_versions | Does not exist | **Yes** — core of reproducibility |
| Rules + Parameters | JSON on StrategyVersion | Does not exist | **Yes** — core of reproducibility |
| Filter config | JSON on Run (AnalyticsFilter dump) | AnalyticsFilter model exists but not stored | **Yes** — add as JSON field |
| Engine version | `analytics_engine_version` str field | Does not exist | **Yes** — git hash at run time |
| Execution timestamp | `created_at` on Run | Standard timestamp mixin | **Yes** — already in base model |
| Metrics results | RunMetric rows | Does not exist | **Yes** — captures the outcome |
| Random seed | Stored in params JSON | Edge Discovery has `seed` param | **Yes** — for stochastic comparisons |

### Existing Snapshot Pattern (Reusable)

The **Edge Discovery snapshot** pattern is the template:

```python
# From edge_discovery/implementations/sqlite_edge_repository.py
# Snapshot stored as a single row with JSON blob:
INSERT INTO edge_snapshots
    (snapshot_id, created_at, trade_count, group_count, params, rankings)
VALUES (?, ?, ?, ?, ?, ?)
```

Key properties:
- **Write-once, read-many** — immutable after storage
- **Params as JSON** — full reproducibility of generation parameters
- **Seed stored** — deterministic reproduction
- **Timestamps** — when was it computed

### What Needs to Be Built

1. **New tables**: `strategy_versions`, `experiments`, `runs`, `run_metrics` — in the main `trading_journal.db` (same SQLite DB, new tables only, no touch to existing ones)
2. **New module**: `backend/app/modules/strategy_lab/` — all new code
3. **Entity models**: SQLAlchemy models for the 4 new entities
4. **Schemas**: Pydantic request/response models
5. **Service**: `StrategyLabService` — orchestrates creation, execution, and comparison
6. **Comparison engine**: `StrategyComparisonEngine` — bootstrap-based statistical comparison
7. **Walk-forward orchestrator**: Logic to slice date ranges and run analytics per window
8. **Engine version detection**: Read git commit hash at startup (or store in a static `VERSION` file)

### What Already Supports This

| Code | Supports |
|------|----------|
| `AnalyticsFilter` + `list_closed(date_from, date_to)` | Time-range filtered queries |
| `compute_performance()` | Deterministic, single-pass metrics |
| `compute_risk()` | Deterministic, single-pass metrics |
| `NumpyStatisticsEngine` | Bootstrap CI and p-values |
| `SqliteEdgeRepository.save_snapshot()` pattern | Write-once immutable storage |
| `EdgeDiscoveryEngine.generate()` pattern | Async background generation |
| `UnitOfWork` pattern | Transaction boundary, repository injection |

### What Must NOT Be Touched

- `app/models/trade.py` — journal SSOT
- `app/models/strategy.py` — base catalog entity
- `app/models/base.py` — base model (unless extending for new entities is needed)
- `app/modules/analytics/calculators/` — pure calculation functions (reuse via import)
- `app/modules/edge_discovery/` — independent module, may import from it
- `app/modules/trades/` — journal management
- Any existing migration files

---

## Affected Areas (Summary)

| Path | Why Affected | Change Type |
|------|-------------|-------------|
| `backend/app/models/` — new files | `strategy_version.py`, `experiment.py`, `run.py`, `run_metric.py` | **New** |
| `backend/app/modules/strategy_lab/` | New module: all strategy lab logic | **New** |
| `backend/app/models/__init__.py` | Export new models | **Update** |
| `backend/app/db/unit_of_work.py` | New repositories for Strategy Lab entities | **Update** |
| `backend/alembic/versions/` | Migration for 4 new tables | **New** |
| `backend/app/modules/analytics/service.py` | Reused (not modified) | Import only |
| `backend/app/modules/edge_discovery/implementations/numpy_statistics_engine.py` | Reused for comparison | Import only |
| `backend/app/modules/analytics/calculators/performance.py` | Reused | Import only |
| `openspec/changes/strategy-lab/` | SDD artifacts | **New** |

---

## Approaches Comparison

### 1. Strategy Version Storage

| Approach | Pros | Cons | Effort |
|----------|------|------|--------|
| **A: New StrategyVersion table** | Isolated from journal, supports full versioning, JSON params | More tables to manage | **Medium** |
| B: Add version fields to Strategy table | Simpler schema | Touches journal model, violates journal invariance | Low |
| C: JSON blob store (edge_cache.db) | Fully isolated, no schema migration | No relational integrity, harder to query | Low |

**Recommendation**: A. New `StrategyVersion` table in `trading_journal.db` (same DB, separate table).

### 2. Run Storage Pattern

| Approach | Pros | Cons | Effort |
|----------|------|------|--------|
| **A: Normalized Run + RunMetric tables** | Queryable, relational integrity | More SQL | **Medium** |
| B: Single Run table with JSON metrics | Simpler, fewer joins | Hard to query individual metrics | Medium |
| C: Edge Cache-style separate DB | Fully isolated | Cross-DB joins impossible | Medium |

**Recommendation**: A. Normalized Run + RunMetric tables in main DB.

### 3. Statistical Comparison

| Approach | Pros | Cons | Effort |
|----------|------|------|--------|
| **A: New Bootstrap-based ComparisonEngine** | Clean, pure, reusable | Need to implement permutation test | **Medium** |
| B: Reuse edge discovery engine directly | Already exists | Designed for dimension grouping, not pairwise comparison | Medium |
| C: Use scipy (add dependency) | Battle-tested stats | Adds dependency, overkill for bootstrap | Low |

**Recommendation**: A. Build a lightweight `ComparisonEngine` that imports numpy from `NumpyStatisticsEngine` and adds permutation testing.

---

## Risks

1. **Scope creep**: Statistical comparison (Q5) and walk-forward (Q4) could each be their own feature. Consider them Phase 2 if MVP pressure is high.
2. **AnalyticsFilter date filtering**: `list_closed()` filters on `exit_datetime`, not `entry_datetime`. This means a trade opened before `date_from` but closed inside the window will be included. This is actually **correct** for performance analysis (PnL crystallizes on exit), but must be documented.
3. **Engine version detection**: Need a mechanism to capture the current git commit hash at runtime. Options: environment variable, `VERSION` file, or `importlib.metadata`. None exist today.
4. **Seed reproducibility**: The comparison engine uses bootstrap with random seeds. If the underlying numpy random generator changes (version bump), results may differ. Document this explicitly.
5. **Large walk-forward datasets**: Running N sequential analytics queries against the DB could be slow. Consider batching or caching for large trade sets.
6. **No rules DSL**: Phase 1 treats "rules" as metadata (human-readable + hash). True rule versioning requires a DSL or code snapshot mechanism, which is a significant effort.

---

## Ready for Proposal

**Yes**. The exploration has clarified all 6 discovery questions with concrete findings and recommendations. The orchestrator can proceed to the Proposal phase with:

1. Clear entity model (StrategyVersion, Experiment, Run, RunMetric)
2. Clear reuse boundaries (analytics calculators = import, edge discovery statistics = import)
3. Clear non-negotiable constraints (journal untouched, no analytics duplication, no generative AI)
4. Clear scope boundaries (Phase 1 = strategy versioning + run execution + comparison; Phase 2 = walk-forward + rules DSL)

---

## Appendix: Key File Paths

### Models (existing)
| File | Purpose |
|------|---------|
| `backend/app/models/base.py` | Base, TimestampMixin, SoftDeleteMixin |
| `backend/app/models/strategy.py` | Strategy, Setup, StrategySetup |
| `backend/app/models/trade.py` | Trade — canonical SSOT |
| `backend/app/models/tag.py` | Tag — free-form categorization |
| `backend/app/models/mistake.py` | Mistake — trading error types |
| `backend/app/models/account.py` | Account — trading accounts |
| `backend/app/models/asset.py` | Asset — tradeable instruments |
| `backend/app/models/catalogs.py` | Market, MarketSession, Timeframe, Broker |

### Modules (existing)
| File | Purpose |
|------|---------|
| `backend/app/modules/analytics/service.py` | AnalyticsService — read-only orchestrator |
| `backend/app/modules/analytics/calculators/performance.py` | compute_performance() |
| `backend/app/modules/analytics/calculators/risk.py` | compute_risk(), sharpe, sortino, calmar |
| `backend/app/modules/analytics/calculators/rolling.py` | compute_rolling_metrics() |
| `backend/app/modules/analytics/schemas.py` | AnalyticsFilter, all response models |
| `backend/app/modules/analytics/router.py` | REST endpoints |
| `backend/app/modules/edge_discovery/engine/edge_discovery_engine.py` | Full pipeline orchestrator |
| `backend/app/modules/edge_discovery/engine/scorer.py` | Composite edge score |
| `backend/app/modules/edge_discovery/engine/statistical_gate.py` | Confidence gating |
| `backend/app/modules/edge_discovery/engine/stability.py` | Split-half stability |
| `backend/app/modules/edge_discovery/engine/fdr.py` | Benjamini-Hochberg |
| `backend/app/modules/edge_discovery/engine/combinator.py` | Dimension grouping |
| `backend/app/modules/edge_discovery/implementations/numpy_statistics_engine.py` | Bootstrap CI, p-value |
| `backend/app/modules/edge_discovery/implementations/sqlite_edge_repository.py` | Snapshot storage |
| `backend/app/modules/edge_discovery/service.py` | Service layer |
| `backend/app/modules/catalogs/repository.py` | CatalogRepository |
| `backend/app/modules/trades/repository.py` | TradeRepository.list_closed() |
| `backend/app/modules/strategies/router.py` | **Scaffold only** |
| `backend/app/modules/risk_management/` | **Scaffold only** |
| `backend/app/modules/ai_insights/schemas.py` | InsightContext, Insight (interprets results only) |
| `backend/app/db/unit_of_work.py` | UnitOfWork — repository injection |
| `backend/app/database.py` | SQLite engine, session factory |

### Migrations
| File | Purpose |
|------|---------|
| `backend/alembic/versions/970bf55b0d74_create_strategy_cluster_tables.py` | Creates strategies, setups, risk_profiles |
| `backend/alembic/versions/2e3b2ebec6d5_create_account_asset_trade_tables.py` | Core journal tables |
