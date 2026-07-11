# Tasks: v1.4.0 Edge Discovery

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~2,500 (1,200 backend + 650 frontend + 650 tests) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | 4 work units (see below) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main (user confirmed) |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main (user confirmed)
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Backend Core (interfaces, engine, storage) | PR 1 | `pytest tests/modules/edge_discovery/ -k "unit" --no-header -q` | POST generate with known trade fixture → verify snapshot written | Revert PR 1 — isolated data layer, no endpoints |
| 2 | Backend API (service, router, orchestrator, numpy) | PR 2 | `pytest tests/modules/edge_discovery/ -k "integration or router" --no-header -q` | TestClient test suite on /analytics/edges/* | Revert PR 2 — no frontend coupling |
| 3 | Frontend (types, service, hooks, components, pages) | PR 3 | `cd frontend && npx vitest run modules/edge-discovery/` | `npm run dev` → navigate to /analytics/edges | Revert PR 3 — UI only, no backend changes |
| 4 | Tests + polish | PR 4 | Full backend + frontend test suite | Both test suites green | Revert PR 4 — test-only changes |

---

## Phase 1: Foundation (interfaces, models, dependencies)

### [x] Task 1: Domain models and API schemas
**Priority**: P0
**Effort**: M
**Dependencies**: None
**Files**: `backend/app/modules/edge_discovery/schemas.py`, `backend/app/modules/edge_discovery/models.py`
- **Acceptance Criteria**:
  - `EdgeScore` Pydantic model matches all 10 contracted fields verbatim
  - `EdgeRankingResponse`, `EdgeDetailResponse`, `SnapshotInfo`, `SnapshotListResponse`, `TagImpact`, `MistakeImpact` schemas match the design
  - Pydantic v2 validators for `confidence_level` Literal type
- **Sub-tasks**:
  1. Create `schemas.py` with all response schemas
  2. Create `models.py` with `EdgeGenerateRequest` (min_observations, bootstrap_resamples, fdr_alpha, stability_threshold, seed) and internal types
  3. Add `failure_reasons: list[str]` to EdgeScore for gate transparency

### [x] Task 2: AbstractStatisticsEngine interface
**Priority**: P0
**Effort**: S
**Dependencies**: None
**Files**: `backend/app/modules/edge_discovery/interface/__init__.py`, `backend/app/modules/edge_discovery/interface/statistics_engine.py`
- **Acceptance Criteria**:
  - ABC with 4 abstract methods: `compute_bootstrap_ci`, `compute_p_value`, `benjamini_hochberg`, `compute_stability_score`
  - Signatures match design contract exactly
  - Zero numpy imports anywhere in interface
- **Sub-tasks**:
  1. Create `interface/__init__.py`
  2. Create `interface/statistics_engine.py` with ABC and method stubs

### [x] Task 3: AbstractEdgeRepository interface
**Priority**: P0
**Effort**: S
**Dependencies**: Task 1
**Files**: `backend/app/modules/edge_discovery/interface/edge_repository.py`
- **Acceptance Criteria**:
  - ABC with 7 abstract methods: `save_snapshot`, `get_latest_snapshot`, `get_edge`, `list_snapshots`, `get_snapshot`, `get_tag_impact`, `get_mistake_impact`
  - Methods are async, return types match design
  - `save_snapshot` returns `str` (snapshot_id)
- **Sub-tasks**:
  1. Create `interface/edge_repository.py` with ABC
  2. All methods accept `**kwargs` only (no positional args)

### [x] Task 4: Module scaffolding and DI
**Priority**: P0
**Effort**: S
**Dependencies**: None
**Files**: `backend/app/modules/edge_discovery/__init__.py`, `backend/app/modules/edge_discovery/dependencies.py`
- **Acceptance Criteria**:
  - `dependencies.py` provides `get_edge_repository()` and `get_edge_discovery_service()` FastDI providers
  - Module init file exports nothing (scaffolding only)
- **Sub-tasks**:
  1. Create `__init__.py`
  2. Create `dependencies.py` with lazy SQLite connection and service providers

---

## Phase 2: Core Engine

### [x] Task 5: Combinator — dimension group enumeration
**Priority**: P0
**Effort**: M
**Dependencies**: Task 1
**Files**: `backend/app/modules/edge_discovery/engine/__init__.py`, `backend/app/modules/edge_discovery/engine/combinator.py`
- **Acceptance Criteria**:
  - `enumerate(trades)` returns list of groups with `{dimensions, trade_ids, trades}`
  - Groups are deduped by existing dimension values (not Cartesian product)
  - Dimensions: strategy, setup, session, asset, direction (null-safe FK handling)
  - Deterministic: same trades → same groups
- **Sub-tasks**:
  1. Create `engine/__init__.py`
  2. Implement `Combinator.enumerate()` that iterates all trades, groups by 5-tuple
  3. Generate deterministic `group_id` as hash of dimension tuple

### [x] Task 6: Scorer — per-group metrics + composite edge_score
**Priority**: P0
**Effort**: M
**Dependencies**: Task 1, Task 5
**Files**: `backend/app/modules/edge_discovery/engine/scorer.py`
- **Acceptance Criteria**:
  - `compute_edge_score(group)` returns `EdgeScore` with all fields populated
  - Core metrics: expectancy, net_pnl, profit_factor from group PnL list
  - Composite formula matches design: `abs(expectancy) * edge_strength * stability_weight * fdr_penalty`
  - Empty/single-trade groups handled with zero/None fallbacks
- **Sub-tasks**:
  1. Implement `compute_metrics(group_trades)` → dict of core metrics
  2. Implement `compute_edge_score(group, ci, p_value, fdr_p, stability)` → EdgeScore
  3. Implement composite formula from design

### [x] Task 7: Statistical Gate (pure function per ADR-011)
**Priority**: P0
**Effort**: S
**Dependencies**: Task 1
**Files**: `backend/app/modules/edge_discovery/engine/statistical_gate.py`
- **Acceptance Criteria**:
  - `determine_confidence_level(...)` returns `(confidence_level, failure_reasons)`
  - Gate 1: trade_count >= min_observations (default 30)
  - Gate 2: CI lower > 0
  - Gate 3: fdr_adjusted_p_value <= alpha (default 0.10)
  - Gate 4: stability_score >= threshold (default 0.5)
  - Level mapping matches ADR-011: high (>=0.8), medium (>=0.5), low (<0.5), insufficient (failures)
  - Pure function — zero dependencies
- **Sub-tasks**:
  1. Implement `determine_confidence_level()` with all 4 gates
  2. Export `DEFAULT_MIN_OBSERVATIONS`, `DEFAULT_FDR_ALPHA`, `DEFAULT_STABILITY_THRESHOLD`

### [x] Task 8: Benjamini-Hochberg FDR correction
**Priority**: P0
**Effort**: S
**Dependencies**: None
**Files**: `backend/app/modules/edge_discovery/engine/fdr.py`
- **Acceptance Criteria**:
  - `benjamini_hochberg(p_values, alpha=0.10)` returns adjusted p-values preserving input order
  - Pure Python implementation (~15 lines, no numpy)
  - Matches known reference output for a small test set
- **Sub-tasks**:
  1. Implement BH procedure with rank-based correction
  2. Add monotonicity enforcement (p-values non-decreasing after correction)

### [x] Task 9: Split-half stability test
**Priority**: P0
**Effort**: S
**Dependencies**: None
**Files**: `backend/app/modules/edge_discovery/engine/stability.py`
- **Acceptance Criteria**:
  - `compute_stability_score(first_half, second_half)` → float 0-1
  - Chronological split by `exit_datetime` (earliest 50% vs latest 50%)
  - 1.0 = identical halves; 0.0 = opposite directions
  - Edge cases: 0 trades → 0.0, 1 trade → 1.0 (degenerate)
- **Sub-tasks**:
  1. Implement split-half using correlation of cumulative PnL vectors
  2. Handle degenerate cases (insufficient trades for split)

---

## Phase 3: Storage

### [x] Task 10: SQLite connection management
**Priority**: P0
**Effort**: S
**Dependencies**: None
**Files**: `backend/app/modules/edge_discovery/db.py`
- **Acceptance Criteria**:
  - `get_edge_cache_connection()` returns async `aiosqlite.Connection`
  - Database path: `data/edge_cache.db` (lazy-created, relative to project root)
  - Connection is lazily initialized on first call, not at import time
  - Creates `edge_snapshots` table if not exists
- **Sub-tasks**:
  1. Implement `get_edge_cache_db()` with connection factory
  2. Implement `ensure_schema()` with `CREATE TABLE IF NOT EXISTS` DDL
  3. Create index `idx_snapshots_created_at` on `created_at DESC`

### [x] Task 11: SqliteEdgeRepository (ADDED get_rankings as 8th method — needed by engine)
**Priority**: P0
**Effort**: L
**Dependencies**: Task 1, Task 10
**Files**: `backend/app/modules/edge_discovery/implementations/__init__.py`, `backend/app/modules/edge_discovery/implementations/sqlite_edge_repository.py`
- **Acceptance Criteria**:
  - Implements all 7 abstract methods from `AbstractEdgeRepository`
  - `save_snapshot` stores JSON results + parameters; returns UUID
  - `get_latest_snapshot` queries `ORDER BY created_at DESC LIMIT 1`
  - `get_edge` loads latest snapshot results and filters by `group_id`
  - `get_tag_impact` / `get_mistake_impact` computes on-the-fly from latest snapshot trades
  - Results parsed through Pydantic EdgeScore on read
  - Snapshot immutable: never UPDATE or DELETE
- **Sub-tasks**:
  1. Implement `save_snapshot(rankings, parameters)` with UUID generation
  2. Implement `get_latest_snapshot()` → list of EdgeScore objects
  3. Implement `get_edge(group_id)` with JSON extraction in Python after load
  4. Implement `list_snapshots()` → SnapshotInfo list
  5. Implement `get_snapshot(snapshot_id)` → full snapshot
  6. Implement `get_tag_impact()` and `get_mistake_impact()`

---

## Phase 4: Implementation

### [x] Task 12: NumpyStatisticsEngine
**Priority**: P0
**Effort**: M
**Dependencies**: Task 2, Task 8
**Files**: `backend/app/modules/edge_discovery/implementations/numpy_statistics_engine.py`, `backend/pyproject.toml`
- **Acceptance Criteria**:
  - Implements all 4 methods from AbstractStatisticsEngine using numpy
  - `compute_bootstrap_ci`: percentile bootstrap with configurable resamples (default 10K) and CI (default 0.95)
  - `compute_p_value`: one-sided, proportion of resamples ≤ null hypothesis
  - `benjamini_hochberg`: delegates to pure function from engine/fdr.py (interface method wraps it)
  - `compute_stability_score`: delegates to engine/stability.py (interface method wraps it)
  - Zero numpy imports outside this file
  - `numpy>=1.26` added to pyproject.toml dependencies
- **Sub-tasks**:
  1. Add `numpy>=1.26` to `pyproject.toml` `[project] dependencies`
  2. Implement `NumpyStatisticsEngine` with bootstrap CI using `numpy.percentile`
  3. Implement p-value via bootstrap resampling count
  4. Delegate BH and stability to pure function implementations
  5. Install deps: `pip install numpy` or `uv add numpy`

### [x] Task 13: EdgeDiscoveryEngine — orchestrator
**Priority**: P0
**Effort**: L
**Dependencies**: Task 5, Task 6, Task 7, Task 8, Task 9, Task 11, Task 12
**Files**: `backend/app/modules/edge_discovery/engine/edge_discovery_engine.py`
- **Acceptance Criteria**:
  - `generate()` full pipeline: load trades → enumerate → score → correct → test → store
  - Accepts `EdgeGenerateRequest` parameters (min_observations, bootstrap_resamples, fdr_alpha, stability_threshold, seed)
  - Seed passed to numpy for reproducibility
  - `confidence_level` assigned via statistical gate per group
  - EdgeScore records sorted by `edge_score DESC` before storage
  - Returns `snapshot_id`
- **Sub-tasks**:
  1. Implement `__init__(uow, stats_engine, edge_repo)` with DI
  2. Implement `generate(params)` orchestration pipeline
  3. Trade loading via `uow.trades.list_closed(load_relations=[strategy, setup, tags, mistakes])`
  4. Group enum → per-group scoring → aggregate FDR → per-group gate + stability → store

---

## Phase 5: API

### [x] Task 14: EdgeDiscoveryService
**Priority**: P0
**Effort**: M
**Dependencies**: Task 3, Task 11, Task 13
**Files**: `backend/app/modules/edge_discovery/service.py`
- **Acceptance Criteria**:
  - `generate(request)` validates params, launches background task
  - `get_rankings(show_insufficient=False)` → EdgeRankingResponse from latest snapshot
  - `get_edge_detail(group_id)` → EdgeScore + trade list for drill-down
  - `get_tag_impact()` / `get_mistake_impact()` → TagImpact/MistakeImpact lists
  - `list_snapshots()` → SnapshotListResponse
  - `get_snapshot(snapshot_id)` → EdgeRankingResponse for specific version
  - All methods degrade gracefully (empty snapshot → empty list, not 500)
- **Sub-tasks**:
  1. [x] Implement service class with constructor injection
  2. [x] `generate()` uses `BackgroundTasks` for async generation
  3. [x] All read methods query repository, transform to response schemas

### [x] Task 15: API Router + endpoints
**Priority**: P0
**Effort**: M
**Dependencies**: Task 14
**Files**: `backend/app/modules/edge_discovery/router.py`
- **Acceptance Criteria**:
  - `APIRouter(prefix="/api/analytics/edges", tags=["edge-discovery"])`
  - POST `/generate` — admin-only, 202 accepted, returns `{"snapshot_id": "..."}`
  - GET `/` — `show_insufficient` query param (default false)
  - GET `/{group_id}` — 404 if missing
  - GET `/tags` — tag impact ranking
  - GET `/mistakes` — mistake impact ranking
  - GET `/snapshots` — list all snapshots
  - GET `/snapshots/{id}` — specific snapshot, 404 if missing
  - Admin auth check on POST (reuse existing pattern from codebase)
- **Sub-tasks**:
  1. [x] Create router with all 7 endpoints
  2. [x] Wire auth dependency for POST generate
  3. [x] Add `show_insufficient` query to GET /

---

## Phase 6: Frontend

### [x] Task 16: Frontend types and API service
**Priority**: P1
**Effort**: S
**Dependencies**: Task 1 (API contract)
**Files**: `frontend/src/modules/edge-discovery/types/edge-discovery.ts`, `frontend/src/modules/edge-discovery/services/edge-discovery.service.ts`
- **Acceptance Criteria**:
  - JSDoc type definitions (project uses JS not TS): `EdgeScore`, `EdgeRankingResponse`, `EdgeDetailResponse`, `TagImpact`, `MistakeImpact`, `SnapshotInfo`, `SnapshotListResponse`
  - Service exposes: `generate()`, `getRankings(showInsufficient?)`, `getEdge(groupId)`, `getTags()`, `getMistakes()`, `listSnapshots()`, `getSnapshot(id)`
  - Uses shared `api` from `shared/lib/api`
- **Sub-tasks**:
  1. [x] Create type definitions matching backend schemas (JSDoc in JS)
  2. [x] Create API service with all methods

### [x] Task 17: React Query hooks
**Priority**: P1
**Effort**: S
**Dependencies**: Task 16
**Files**: `frontend/src/modules/edge-discovery/hooks/useEdgeRankings.ts`, `frontend/src/modules/edge-discovery/hooks/useEdgeDetail.ts`
- **Acceptance Criteria**:
  - `useEdgeRankings(showInsufficient?)` — query key `['edge-discovery', 'rankings', showInsufficient]`
  - `useEdgeDetail(groupId)` — query key `['edge-discovery', 'detail', groupId]`
  - Follows existing hook patterns (see `useEquity.js`)
  - Auto-refetch disabled (snapshots are point-in-time)
- **Sub-tasks**:
  1. [x] Create `useEdgeRankings.ts` hook
  2. [x] Create `useEdgeDetail.ts` hook

### [x] Task 18: EdgeDiscovery frontend components
**Priority**: P1
**Effort**: L
**Dependencies**: Task 16
**Files**: `frontend/src/modules/edge-discovery/components/EdgeRankingTable.tsx`, `frontend/src/modules/edge-discovery/components/EdgeScoreCard.tsx`, `frontend/src/modules/edge-discovery/components/EdgeDetailDrilldown.tsx`, `frontend/src/modules/edge-discovery/components/EdgeStabilityIndicator.tsx`
- **Acceptance Criteria**:
  - `EdgeRankingTable`: sortable by edge_score, columns include dimensions, expectancy, CI, stability, confidence_level badge; hidden `insufficient` by default with toggle
  - `EdgeScoreCard`: visual card showing expectancy, p-value, CI range, stability score; color-coded border by confidence level
  - `EdgeDetailDrilldown`: table of trade_ids linked to trade detail page, summary metrics header
  - `EdgeStabilityIndicator`: badge component — green (high), yellow (medium), gray (low), red (insufficient)
  - All components handle loading skeleton (using shared Skeleton), empty, and error states
  - Reuse shared primitives from `frontend/src/shared/components/`
- **Sub-tasks**:
  1. [x] Implement `EdgeStabilityIndicator` (smallest, foundation for others)
  2. [x] Implement `EdgeScoreCard`
  3. [x] Implement `EdgeRankingTable`
  4. [x] Implement `EdgeDetailDrilldown`

### [x] Task 19: Frontend pages and routing
**Priority**: P1
**Effort**: M
**Dependencies**: Task 17, Task 18
**Files**: `frontend/src/modules/edge-discovery/pages/EdgeDiscoveryPage.tsx`, `frontend/src/modules/edge-discovery/pages/EdgeDetailPage.tsx`, `frontend/src/modules/edge-discovery/index.tsx`, `frontend/src/App.jsx`
- **Acceptance Criteria**:
  - `EdgeDiscoveryPage`: renders EdgeRankingTable, generate button, filter for show_insufficient
  - `EdgeDetailPage`: renders EdgeScoreCard + EdgeDetailDrilldown, back button to rankings
  - Route `/analytics/edges` → EdgeDiscoveryPage, `/analytics/edges/:group_id` → EdgeDetailPage
  - Route added to `App.jsx` with `lazy()` import
  - Module entry `index.tsx` exports pattern
- **Sub-tasks**:
  1. [x] Create `EdgeDiscoveryPage.tsx`
  2. [x] Create `EdgeDetailPage.tsx`
  3. [x] Create `index.tsx` module entry
  4. [x] Add lazy route in `App.jsx`

---

## Phase 7: Integration (tests, wiring, docs)

### [x] Task 20: Backend unit tests — engine components
**Priority**: P1
**Effort**: L
**Dependencies**: Task 5, Task 6, Task 7, Task 8, Task 9
**Files**: `backend/tests/modules/edge_discovery/test_combinator.py`, `backend/tests/modules/edge_discovery/test_scorer.py`, `backend/tests/modules/edge_discovery/test_fdr.py`, `backend/tests/modules/edge_discovery/test_stability.py`, `backend/tests/modules/edge_discovery/test_statistical_gate.py`
- **Acceptance Criteria**:
  - Combinator: known trades → expected groups; null FK → correct grouping; no invalid combos
  - Scorer: known pnl list → expected expectancy, net_pnl, profit_factor; empty trades → zeros
  - FDR: manual BH reference for small p-value list; preserves order; monotonicity
  - Stability: identical halves → 1.0; opposite → 0.0; degenerate cases
  - Statistical gate: all gates independently testable; parameter overrides work
  - Follows existing `test_calculators.py` pattern with `MagicMock` Trade objects
- **Sub-tasks**:
  1. Write `test_combinator.py` (3-4 test cases)
  2. Write `test_scorer.py` (3-4 test cases)
  3. Write `test_fdr.py` (2-3 test cases with known reference)
  4. Write `test_stability.py` (3-4 edge cases)
  5. Write `test_statistical_gate.py` (4-5 cases covering all gate combos)

### [x] Task 21: Backend unit tests — implementations
**Priority**: P1
**Effort**: M
**Dependencies**: Task 11, Task 12
**Files**: `backend/tests/modules/edge_discovery/test_sqlite_edge_repository.py`, `backend/tests/modules/edge_discovery/test_numpy_statistics_engine.py`
- **Acceptance Criteria**:
  - SqliteEdgeRepository: in-memory aiosqlite; CRUD round-trips; latest snapshot query; immutability confirmed; tag/mistake impact; empty state
  - NumpyStatisticsEngine: bootstrap CI matches manual np.percentile; p-value for all-positive vs. mixed pnls; reproducible with seed
- **Sub-tasks**:
  1. Write `test_sqlite_edge_repository.py` with in-memory SQLite fixture
  2. Write `test_numpy_statistics_engine.py` with known input/output

### [x] Task 22: Integration + router tests
**Priority**: P1
**Effort**: M
**Dependencies**: Task 13, Task 15
**Files**: `backend/tests/modules/edge_discovery/test_engine.py`, `backend/tests/modules/edge_discovery/test_router.py`
- **Acceptance Criteria**:
  - Engine e2e: mock trade list → real engine + real SqliteEdgeRepository → snapshot stored; verify EdgeScore fields
  - Router: TestClient with mocked service; 200 on data; 422 on invalid params; 404 on missing edge; 202 on generate; auth rejection on POST without admin
  - Empty state: 200 with empty rankings, not 500
- **Sub-tasks**:
  1. [x] Write `test_engine.py` with mocked UOW and real storage
  2. [x] Write `test_router.py` with mocked service

### [x] Task 23: Frontend tests
**Priority**: P2
**Effort**: M
**Dependencies**: Task 17, Task 18
**Files**: `frontend/src/modules/edge-discovery/components/__tests__/EdgeRankingTable.test.tsx`, `frontend/src/modules/edge-discovery/components/__tests__/EdgeScoreCard.test.tsx`, `frontend/src/modules/edge-discovery/components/__tests__/EdgeStabilityIndicator.test.tsx`, `frontend/src/modules/edge-discovery/hooks/__tests__/useEdgeRankings.test.ts`
- **Acceptance Criteria**:
  - Component tests: render with data → correct output; loading skeleton → Skeleton shown; empty state → "No edges found" message; error state → error message
  - Hook test: queries correct endpoint, passes params, returns expected shape
- **Sub-tasks**:
  1. [x] Write EdgeStabilityIndicator test (all 4 confidence levels)
  2. [x] Write EdgeScoreCard test (loading, data, error states)
  3. [x] Write EdgeRankingTable test (sorting, filtering, insufficient toggle)
  4. [x] Write useEdgeRankings hook test (spy on service)
