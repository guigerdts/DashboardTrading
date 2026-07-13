# Tasks: Strategy Lab — Scientific Experiment Framework (v1.6.0)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,700 (400+500+350+450) |
| 600-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | 4 work PRs stacked to main |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Data layer: models, migration, repos, UoW registration | PR #1 | `pytest tests/modules/strategy_lab/test_models.py tests/modules/strategy_lab/test_repository.py -x` | `alembic upgrade head && pytest tests/modules/strategy_lab/test_migration.py` | Revert migration + models + UoW properties |
| 2 | Engine: ComparisonEngine ABC + BootstrapComparisonEngine, version.py, service | PR #2 | `pytest tests/modules/strategy_lab/test_comparison_engine.py tests/modules/strategy_lab/test_service.py -x` | `pytest tests/modules/strategy_lab/test_comparison_flow.py -x` | Revert engine module files, no impact on DB |
| 3 | API: router, schemas, dependencies, integration tests | PR #3 | `pytest tests/modules/strategy_lab/test_router.py tests/modules/strategy_lab/test_execution_flow.py -x` | `httpx-based e2e: pytest tests/modules/strategy_lab/test_execution_flow.py --with-db` | Revert router + schemas + deps |
| 4 | Frontend: API service, hooks, pages, components, tests | PR #4 | `npx jest frontend/src/modules/strategy-lab/` | `npm run dev && navigate /strategy-lab` | Revert frontend/src/modules/strategy-lab/ |

---

## PR #1 — Data Layer (~400 LOC)

- [ ] **1.1 [P1/S]** Create `backend/app/modules/strategy_lab/models.py` — StrategyVersion, Experiment, Run, RunMetric (Base + TimestampMixin, Mapped+mapped_column style). Dependencies: none. Files: models.py.
- [ ] **1.2 [P1/S]** Add `active_version_id` nullable FK + `versions` relationship to `backend/app/models/strategy.py`. Dependencies: 1.1. Files: strategy.py.
- [ ] **1.3 [P1/M]** Create Alembic migration `alembic/versions/XXXX_strategy_lab_v1.py` — revises `ebc4b9c1a9a0`, 4 tables (strategy_versions, experiments, runs, run_metrics) + Strategy FK. Dependencies: 1.1, 1.2. Files: migration file.
- [ ] **1.4 [P1/S]** Add SQLite immutability triggers in migration — BEFORE UPDATE/DELETE on runs/run_metrics, carved-out status update. Dependencies: 1.3. Files: same migration as 1.3.
- [ ] **1.5 [P1/S]** Create `backend/app/modules/strategy_lab/repository.py` — RunRepository (update/delete → NotImplementedError, update_status() with transition validation). Dependencies: 1.1. Files: repository.py.
- [ ] **1.6 [P1/S]** Register 4 lazy-init repos in `backend/app/db/unit_of_work.py` — strategy_versions, experiments, runs (RunRepository), run_metrics. Dependencies: 1.1, 1.5. Files: unit_of_work.py.
- [ ] **1.7 [P2/M]** Create `backend/tests/modules/strategy_lab/test_migration.py` — up/down, trigger enforcement tests. Dependencies: 1.3, 1.4. Files: test_migration.py.
- [ ] **1.8 [P1/S]** Create `backend/app/modules/strategy_lab/__init__.py` — module exports. Dependencies: none. Files: __init__.py.

### Acceptance Criteria
- All 4 new tables exist with correct columns, FKs, and UNIQUE constraints
- Strategy model has `active_version_id` FK (null on delete)
- SQLite triggers block UPDATE (except status) and DELETE on runs/run_metrics
- RunRepository raises NotImplementedError for update/delete
- UoW exposes all 4 repos via lazy-init properties
- Migration up/down passes, triggers fire on violation

---

## PR #2 — Engine (~500 LOC)

- [ ] **2.1 [P1/S]** Create `backend/app/modules/strategy_lab/version.py` — `get_engine_version()` using importlib.metadata then git describe, @lru_cache, RuntimeError on failure. Dependencies: none. Files: version.py.
- [ ] **2.2 [P1/S]** Create `backend/app/modules/strategy_lab/interfaces/comparison_engine.py` — ComparisonEngine ABC + ComparisonResult dataclass. Dependencies: none. Files: interfaces/__init__.py, comparison_engine.py.
- [ ] **2.3 [P1/M]** Create `backend/app/modules/strategy_lab/implementations/bootstrap_comparison_engine.py` — BootstrapComparisonEngine (bootstrap CI of diff, permutation test, Cohen's d). Dependencies: 2.2. Files: implementations/__init__.py, bootstrap_comparison_engine.py.
- [ ] **2.4 [P1/M]** Create `backend/app/modules/strategy_lab/service.py` — StrategyLabService with execute_run() 9-step flow, experiment/version CRUD, compare_runs(). Dependencies: 2.1, 2.2, 2.3, 1.5, 1.6. Files: service.py.
- [ ] **2.5 [P1/M]** Unit tests: `test_version.py` (cache, git fallback, RuntimeError), `test_comparison_engine.py` (known distros → expected p/CI, empty values, identical values, seeding), `test_service.py` (execute_run pipeline, duplicate config, version failure, analytics failure). Dependencies: 2.1, 2.3, 2.4. Files: 3 test files.

### Acceptance Criteria
- `get_engine_version()` returns string or raises RuntimeError (never falls back silently)
- ComparisonEngine ABC is pure interface — domain code depends on ABC, not impl
- BootstrapComparisonEngine produces correct CI/p-value for known distributions
- StrategyLabService.execute_run() follows the 9-step flow documented in design §5
- Config identity returns existing Run on match
- engine_version stored as non-empty string in every Run
- RunMetrics only created when baseline_run_id is set (comparison metrics)

---

## PR #3 — API Layer (~350 LOC)

- [ ] **3.1 [P1/S]** Create `backend/app/modules/strategy_lab/schemas.py` — Pydantic models for all request/response (ExperimentCreate, RunCreate, StrategyVersionCreate, ComparisonResponse). No engine_version in any request schema. Dependencies: 1.1. Files: schemas.py.
- [ ] **3.2 [P1/M]** Create `backend/app/modules/strategy_lab/router.py` — 15 endpoints: 5 experiments, 4 runs, 1 comparison, 3 strategy versions, 1 set active version, 1 list metrics. No PUT/PATCH/DELETE routes for runs (except PATCH status). Dependencies: 3.1, 2.4. Files: router.py.
- [ ] **3.3 [P1/S]** Create `backend/app/modules/strategy_lab/dependencies.py` — DI providers: get_comparison_engine(), get_strategy_lab_service(). Dependencies: 2.2, 2.3, 2.4. Files: dependencies.py.
- [ ] **3.4 [P1/M]** Integration tests: `test_router.py` (httpx — all endpoints 201/200/404/422/500), `test_execution_flow.py` (create version → experiment → run → verify), `test_config_identity.py` (same POST × 2 → same Run), `test_comparison_flow.py` (2 runs → compare → RunMetrics). Dependencies: 3.1, 3.2, 3.3. Files: 4 test files.
- [ ] **3.5 [P2/S]** Error handling tests: 404 for missing entities, 422 for invalid status transitions, 409 for version duplicate, 500 for engine version failure. Dependencies: 3.4. Files: included in 3.4.

### Acceptance Criteria
- All 15 endpoints respond with correct status codes and body shape
- No engine_version in any POST/PATCH request schema (auto-captured only)
- No PUT/PATCH/DELETE routes for runs except PATCH status
- Comparison endpoint validates same strategy_version_id, returns 400 for mismatch
- Pydantic validation rejects invalid JSON, empty names, bad UUIDs
- Engine version failure returns 500 without Run creation

---

## PR #4 — Frontend (~450 LOC)

- [ ] **4.1 [P1/S]** Create `frontend/src/modules/strategy-lab/services/strategyLabApi.js` — API service object with methods for all endpoints, following analyticsApi pattern. Dependencies: none. Files: services/strategyLabApi.js.
- [ ] **4.2 [P1/S]** Create hooks: `useExperiments.js`, `useRuns.js`, `useComparison.js`, `useStrategyVersions.js` — React Query useQuery/useMutation with proper invalidation. Dependencies: 4.1. Files: hooks/*.js + utils/constants.js.
- [ ] **4.3 [P1/S]** Create `ExperimentList.jsx` (table + loading/error/empty states) + `CreateExperimentDialog.jsx` (form validation + submit). Dependencies: 4.2. Files: components/*.jsx.
- [ ] **4.4 [P1/S]** Create `RunDetail.jsx` (header, reproducibility card, status badge, metrics table) + `RunMetricsTable.jsx` (color-coded p-values). Dependencies: 4.2. Files: components/*.jsx.
- [ ] **4.5 [P1/M]** Create `ComparisonView.jsx` — side-by-side layout, Run A | Run B | delta column, CI visualization, p-value highlighting. Dependencies: 4.2. Files: components/ComparisonView.jsx.
- [ ] **4.6 [P1/S]** Create pages: `StrategyLabPage.jsx` (experiment list + create), `ExperimentDetailPage.jsx` (runs + comparison). Dependencies: 4.3, 4.4, 4.5. Files: pages/*.jsx.
- [ ] **4.7 [P2/S]** Lazy route registration in `App.jsx`. Dependencies: 4.6. Files: App.jsx.
- [ ] **4.8 [P2/M]** Hook tests + component tests: ExperimentList (4 states), CreateExperimentDialog (validation, submit, error), RunDetail (metrics, status), ComparisonView (layout, delta, significance, not-comparable). Dependencies: 4.3-4.6. Files: __tests__/*.test.jsx.

### Acceptance Criteria
- All 4 data states (loading/error/empty/success) rendered per component
- Experiment list shows: name, hypothesis, status, run count, date
- Run detail shows: reproducibility card, metrics table, status badge
- ComparisonView shows: side-by-side columns, delta, CI, p-value, significance coloring
- Create experiment form validates and shows loading state on submit
- "Not comparable" warning when strategy versions differ
- Lazy route loads module without breaking existing routes

---

## Dependency Graph

```
PR #1 (Data Layer) — no deps
│
└──► PR #2 (Engine) — needs #1 models + UoW repos
    │
    └──► PR #3 (API) — needs #2 service + engine
        │
        └──► PR #4 (Frontend) — needs #3 API
```

Each PR targets main (stacked-to-main). Each PR independently passes tests after merge. No PR exceeds 600 LOC.

## Mandatory Principles (Non-Negotiable)

| Principle | Enforcement |
|-----------|-------------|
| Run immutability | SQLite triggers + RunRepository override + no PUT/DELETE routes |
| RunMetric = only expensive results | NEVER basic metrics (PF, win_rate, sharpe, drawdown) |
| Engine version mandatory + automatic | RuntimeError if undetectable, no user field in schemas |
| ComparisonEngine behind ABC | Service depends on ABC, never on BootstrapComparisonEngine directly |
| No analytics/risk/edge duplication | AnalyticsService called for basic metrics, results not persisted |
