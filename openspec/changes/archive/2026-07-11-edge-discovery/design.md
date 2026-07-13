# Design: v1.4.0 Edge Discovery

## Technical Approach

A standalone `edge_discovery` backend module that enumerates every observed combination of Strategy × Setup × Market Session × Asset × Direction from closed trades, computes statistical scores per group with bootstrap confidence intervals, FDR correction, and split-half stability, then stores versioned snapshots in SQLite. Endpoints are read-only — they query the latest (or a specific) snapshot. Frontend is an independent module with focused ranking/drill-down components. `numpy` is accepted as the first non-stdlib dependency, fully isolated behind `AbstractStatisticsEngine`.

## Architecture Decisions

| Option | Tradeoffs | Decision |
|--------|-----------|----------|
| Module structure: inside `analytics/calculators` vs. standalone `edge_discovery/` | Existing calculator pattern is pure-function dicts; Edge Discovery needs engine state, SQLite config, async generation, and is a different *domain* (statistical vs. aggregational) | **Standalone module** `backend/app/modules/edge_discovery/` — own DI, own schemas, own background orchestration |
| Combination enumeration: SQL GROUP BY vs. Python in-memory | SQL would need N queries or complex multi-dimension pivots; Python gives composability and testability | **Python in-memory** — load all trades once via `list_closed()`, group via dicts |
| Storage: in-memory vs. file vs. SQLite | In-memory loses data on restart; plain file is unqueryable; SQLite supports drill-down and versioning | **SQLite cache table** — dedicated `edge_snapshots` table with JSON results |
| Generation: sync (compute on request) vs. async (background) | Sync would block the app for 10+ seconds with bootstrap × hundreds of groups | **Async generation** — `POST /analytics/edges/generate` launches a background task; endpoints read cached snapshots only |
| Frontend: add to AnalyticsDashboard vs. standalone module | AnalyticsDashboard layout is aggregation-oriented; Edge Discovery needs ranking-focused UI | **Standalone frontend module** `frontend/src/modules/edge-discovery/` — reuse shared UI primitives only |
| Statistics library: pure Python vs. numpy/scipy | Pure Python bootstrap is 10-50× slower; numpy is the first non-stdlib dep but acceptable | **`numpy` accepted** — isolated behind `AbstractStatisticsEngine` interface |
| FDR implementation: scipy.stats vs. manual BH | BH is ~15 lines; no dependency needed | **Manual Benjamini-Hochberg** in `engine/fdr.py` |
| ADR storage: Engram-only vs. files in openspec | ADRs should be discoverable alongside the change they document | **Both** — Engram memory + files in `openspec/changes/edge-discovery/adr-*.md` |

## Data Flow

```
POST /analytics/edges/generate  (admin, triggers background task)
  │
  └─ EdgeDiscoveryEngine.generate()
       ├── trades = uow.trades.list_closed(load_relations=[strategy, setup, tags, mistakes])
       ├── groups = Combinator.enumerate(trades)       # Python in-memory grouping
       │     groups: [{dimensions, trade_ids, trades}, ...]
       │
       ├── for each group:
       │     ├── metrics = compute_metrics(group.trades)  # expectancy, net_pnl, profit_factor
       │     ├── ci_low, ci_high = stats.bootstrap_ci(group.pnls)
       │     └── p_value = stats.compute_p_value(group.pnls)
       │
       ├── adjusted = stats.benjamini_hochberg(all_p_values)
       │
       ├── for each group:
       │     ├── stability = stats.compute_stability_score(half1, half2)
       │     ├── edge_score = composite(expectancy, ci_width, stability)
       │     └── confidence_level = gate(all_criteria)
       │
       ├── EdgeRepository.save_snapshot(rankings)        # immutable SQLite snapshot
       └── return snapshot_id

GET /analytics/edges                                    (read-only)
  └── EdgeRepository.get_latest_snapshot()
       └── return rankings sorted by edge_score desc

GET /analytics/edges/{group_id}                         (drill-down)
  └── EdgeRepository.get_edge(group_id)
       └── return EdgeScore + trade_ids list

GET /analytics/edges/tags                               (tag impact)
  └── EdgeRepository.get_tag_impact()

GET /analytics/edges/mistakes                            (mistake impact)
  └── EdgeRepository.get_mistake_impact()

GET /analytics/edges/snapshots                           (list versions)
  └── EdgeRepository.list_snapshots()

GET /analytics/edges/snapshots/{snapshot_id}             (specific version)
  └── EdgeRepository.get_snapshot(snapshot_id)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/modules/edge_discovery/__init__.py` | Create | Module init |
| `backend/app/modules/edge_discovery/schemas.py` | Create | Request/response Pydantic schemas (EdgeGenerateRequest, EdgeScoreResponse, EdgeRankingResponse, etc.) |
| `backend/app/modules/edge_discovery/models.py` | Create | Internal domain models: EdgeScore, EdgeRanking, TagImpact, MistakeImpact |
| `backend/app/modules/edge_discovery/router.py` | Create | FastAPI router: POST generate, GET edges, GET edges/{id}, GET edges/tags, GET edges/mistakes, GET edges/snapshots, GET edges/snapshots/{id} |
| `backend/app/modules/edge_discovery/service.py` | Create | EdgeDiscoveryService — orchestrates engine, delegates to repository |
| `backend/app/modules/edge_discovery/dependencies.py` | Create | FastAPI DI providers |
| `backend/app/modules/edge_discovery/interface/__init__.py` | Create | |
| `backend/app/modules/edge_discovery/interface/statistics_engine.py` | Create | AbstractStatisticsEngine — bootstrap_ci, compute_p_value, benjamini_hochberg, compute_stability_score |
| `backend/app/modules/edge_discovery/interface/edge_repository.py` | Create | AbstractEdgeRepository — save_snapshot, get_latest_snapshot, get_edge, list_snapshots, get_snapshot, get_tag_impact, get_mistake_impact |
| `backend/app/modules/edge_discovery/engine/__init__.py` | Create | |
| `backend/app/modules/edge_discovery/engine/edge_discovery_engine.py` | Create | Orchestrator: load → enumerate → compute → store |
| `backend/app/modules/edge_discovery/engine/combinator.py` | Create | Enumerates existing dimension combinations from trade list |
| `backend/app/modules/edge_discovery/engine/scorer.py` | Create | Computes EdgeScore per group (metrics + bootstrapped stats) |
| `backend/app/modules/edge_discovery/engine/fdr.py` | Create | Benjamini-Hochberg correction (~15 lines, pure Python) |
| `backend/app/modules/edge_discovery/engine/stability.py` | Create | Split-half stability test (chronological 50/50 by exit_datetime) |
| `backend/app/modules/edge_discovery/implementations/__init__.py` | Create | |
| `backend/app/modules/edge_discovery/implementations/numpy_statistics_engine.py` | Create | numpy implementation of AbstractStatisticsEngine |
| `backend/app/modules/edge_discovery/implementations/sqlite_edge_repository.py` | Create | SQLite implementation of AbstractEdgeRepository |
| `backend/app/modules/edge_discovery/db.py` | Create | SQLite connection management for the edge cache database |
| `frontend/src/modules/edge-discovery/types/edge-discovery.ts` | Create | TypeScript interfaces for EdgeScore, EdgeRanking, etc. |
| `frontend/src/modules/edge-discovery/services/edge-discovery.service.ts` | Create | API bridge (generate, getRankings, getEdge, getTags, getMistakes, listSnapshots) |
| `frontend/src/modules/edge-discovery/hooks/useEdgeRankings.ts` | Create | React Query hook for rankings list |
| `frontend/src/modules/edge-discovery/hooks/useEdgeDetail.ts` | Create | React Query hook for single edge drill-down |
| `frontend/src/modules/edge-discovery/components/EdgeRankingTable.tsx` | Create | Sortable ranking table with significance indicators |
| `frontend/src/modules/edge-discovery/components/EdgeScoreCard.tsx` | Create | Single edge score card with CI, p-value, stability badge |
| `frontend/src/modules/edge-discovery/components/EdgeDetailDrilldown.tsx` | Create | Trade list for a selected edge |
| `frontend/src/modules/edge-discovery/components/EdgeStabilityIndicator.tsx` | Create | Visual badge for stable/unstable/insufficient |
| `frontend/src/modules/edge-discovery/pages/EdgeDiscoveryPage.tsx` | Create | Main rankings page |
| `frontend/src/modules/edge-discovery/pages/EdgeDetailPage.tsx` | Create | Single edge drill-down page |
| `frontend/src/modules/edge-discovery/index.tsx` | Create | Module entry + route definition |
| `backend/requirements.txt` | Modify | Add `numpy>=1.26` |
| `backend/app/api/main.py` | Modify | Register `edge_discovery.router` |

## Interfaces / Contracts

### AbstractStatisticsEngine

```python
from abc import ABC, abstractmethod

class AbstractStatisticsEngine(ABC):
    @abstractmethod
    def compute_bootstrap_ci(
        self, values: list[float], n_resamples: int = 10_000, ci: float = 0.95
    ) -> tuple[float, float]:
        """Percentile bootstrap confidence interval."""
        ...

    @abstractmethod
    def compute_p_value(self, values: list[float], null_hypothesis: float = 0.0) -> float:
        """One-sided p-value: proportion of resamples where ≤ null."""
        ...

    @abstractmethod
    def benjamini_hochberg(
        self, p_values: list[float], alpha: float = 0.10
    ) -> list[float]:
        """Return FDR-adjusted p-values, preserving input order."""
        ...

    @abstractmethod
    def compute_stability_score(
        self, first_half: list[float], second_half: list[float]
    ) -> float:
        """Scalar 0-1: 1 = perfect stability between halves."""
        ...
```

### AbstractEdgeRepository

```python
from abc import ABC, abstractmethod

class AbstractEdgeRepository(ABC):
    @abstractmethod
    async def save_snapshot(
        self, rankings: list[EdgeScore], parameters: dict
    ) -> str:  # returns snapshot_id
        ...

    @abstractmethod
    async def get_latest_snapshot(self) -> list[EdgeScore] | None:
        ...

    @abstractmethod
    async def get_edge(self, group_id: str) -> EdgeScore | None:
        ...

    @abstractmethod
    async def list_snapshots(self) -> list[SnapshotInfo]:
        ...

    @abstractmethod
    async def get_snapshot(self, snapshot_id: str) -> list[EdgeScore] | None:
        ...

    @abstractmethod
    async def get_tag_impact(self) -> list[TagImpact]:
        ...

    @abstractmethod
    async def get_mistake_impact(self) -> list[MistakeImpact]:
        ...
```

### EdgeScore (Pydantic)

```python
from pydantic import BaseModel
from typing import Literal

class EdgeScore(BaseModel):
    # Identity
    group_id: str                         # deterministic hash of the dimension combination
    dimensions: dict[str, str | None]     # {strategy, setup, session, asset, direction}
    trade_ids: list[int]                  # constituent trades for drill-down

    # Core metrics
    trade_count: int
    expectancy: float
    net_pnl: float
    profit_factor: float

    # Statistical validation
    confidence_interval: tuple[float, float]  # 95% bootstrap CI lower, upper
    p_value: float
    fdr_adjusted_p_value: float
    stability_score: float                    # 0-1, 1 = perfect stability

    # Ranking
    edge_score: float                         # composite for sorting
    confidence_level: Literal['high', 'medium', 'low', 'insufficient']
```

### Response Schemas

```python
class EdgeRankingResponse(BaseModel):
    snapshot_id: str
    generated_at: datetime
    total_groups: int
    total_edges: int                           # groups that passed the statistical gate
    rankings: list[EdgeScore]

class EdgeDetailResponse(BaseModel):
    edge: EdgeScore
    trades: list[TradeSummary]                 # lightweight trade list for drill-down

class SnapshotInfo(BaseModel):
    snapshot_id: str
    created_at: datetime
    parameters: dict
    total_groups: int

class SnapshotListResponse(BaseModel):
    snapshots: list[SnapshotInfo]

class TagImpact(BaseModel):
    tag_id: int
    tag_name: str
    trade_count: int
    expectancy: float
    net_pnl: float

class MistakeImpact(BaseModel):
    mistake_id: int
    mistake_name: str
    trade_count: int
    expectancy: float
    net_pnl: float
```

## EdgeScore Composite Formula

```
edge_strength = expectancy / (ci_upper - ci_lower)   # signal-to-noise
stability_weight = stability_score                   # 0..1
fdr_penalty = 1.0 if fdr_adjusted_p_value <= 0.10 else 0.5

edge_score = abs(expectancy) * edge_strength * stability_weight * fdr_penalty
```

Higher edge_score = more reliable edge. Components ensure that wide CIs, unstable splits, and FDR failures all penalize the score.

## SQLite Schema

The edge cache database lives at `data/edge_cache.db` (relative to project root). Table definition:

```sql
CREATE TABLE IF NOT EXISTS edge_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,          -- ISO 8601
    parameters TEXT NOT NULL,          -- JSON
    results TEXT NOT NULL              -- JSON array of EdgeScore records
);

CREATE INDEX idx_snapshots_created_at ON edge_snapshots(created_at DESC);
```

Parameters JSON includes: `min_observations`, `bootstrap_resamples`, `fdr_alpha`, `stability_threshold`, `seed`, `version`.

## Statistical Gate (confidence_level logic)

```
confidence_level = 'insufficient' if ANY of:
  - trade_count < min_observations (default 30)
  - confidence_interval.lower <= 0   (not positive with 95% confidence)
  - fdr_adjusted_p_value > fdr_alpha (default 0.10)
  - stability_score < stability_threshold (default 0.5)

confidence_level = 'high' if:
  - All criteria pass AND stability_score >= 0.8

confidence_level = 'medium' if:
  - All criteria pass AND 0.5 <= stability_score < 0.8

confidence_level = 'low' if:
  - All criteria pass AND stability_score < 0.5  (but >= threshold)
```

Groups with `confidence_level = 'insufficient'` are hidden by default in `GET /analytics/edges` but stored in the snapshot. Admin endpoints MAY accept `show_insufficient: bool` query parameter.

## Routing

The edge discovery router mounts at `/api/analytics/edges` to stay within the analytics namespace (consistent with existing breakdown and risk endpoints), but its service and engine are entirely in the `edge_discovery` module.

```python
router = APIRouter(prefix="/api/analytics/edges", tags=["edge-discovery"])
```

Endpoints:
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/analytics/edges/generate` | admin | Trigger background generation |
| GET | `/api/analytics/edges` | user | Latest ranking (edges only) |
| GET | `/api/analytics/edges/{group_id}` | user | Single edge with trade list |
| GET | `/api/analytics/edges/tags` | user | Tag impact ranking |
| GET | `/api/analytics/edges/mistakes` | user | Mistake impact ranking |
| GET | `/api/analytics/edges/snapshots` | user | List all snapshots |
| GET | `/api/analytics/edges/snapshots/{id}` | user | Specific snapshot |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (Combinator) | Enumeration produces correct groups; only existing combos; null FK handling | Pure function: known trade list → expected group dict |
| Unit (Scorer) | Metric computation per group; empty/single/many trades | Known input → expected EdgeScore |
| Unit (FDR) | BH procedure matches known reference output | Manual calculation vs. function |
| Unit (Stability) | Perfect split = 1.0; identical halves = 1.0; different = < 1.0 | Edge case assertions |
| Unit (NumpyStatisticsEngine) | Bootstrap CI matches percentile calculation; p-value correctness | Compare to scipy.stats bootstrap if available, else manual calculation |
| Unit (SqliteEdgeRepository) | CRUD round-trips; snapshot immutability; latest query | In-memory SQLite with aiosqlite |
| Engine (integration) | End-to-end: load → enumerate → compute → store | Mocked trade list, real engine, real SqliteEdgeRepository |
| Router (integration) | 200 with data; 422 on invalid params; empty state; 404 on missing group | TestClient with mocked service |
| Frontend components | Loading skeleton; error state; empty state; data render | vitest + @testing-library/react |
| Frontend hooks | Query key shape; API delegation; filter passthrough | vitest spying on edge-discovery.service |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. SQLite is local-only, no user input reaches SQL (parameters are stored as JSON, not interpolated).

## Migration / Rollout

No migration required. New module is additive — existing endpoints are untouched. The edge cache SQLite database is created on first use (lazy init in `SqliteEdgeRepository`). The frontend page is accessible via its own route but not linked from the main nav until the module stabilizes.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **numpy dependency** is first non-stdlib dep | Medium | Isolated behind AbstractStatisticsEngine; pure-fallback possible later |
| **Memory**: loading ALL closed trades + all relations could be large (10K+ trades) | Medium | Single `list_closed()` call with eager loading; generation is an admin batch operation, not per-request |
| **CPU**: 10K bootstrap resamples × hundreds of groups = millions of iterations | High | numpy vectorization; async background task (no timeout pressure); configurable `n_resamples` with sensible defaults |
| **Cache staleness**: snapshot does not update automatically after new trades | Medium | Manual re-generation via POST endpoint; snapshot metadata includes generated_at timestamp for transparency |
| **Combination explosion**: N dimensions produce many groups | Low | `Combinator.enumerate()` only emits combos that actually exist in data (not full Cartesian product); most will have < 30 trades and be filtered out |
| **SQLite concurrent access**: background task writes while user reads | Low | Writes create a new snapshot (INSERT); reads query the latest row. No row-level locking conflict since they operate on different rows |

## Open Questions

None — all decisions resolved through the pre-closed decisions and ADRs below.

## ADRs

- [ADR-010: Edge Discovery Snapshots are Versioned and Reproducible](./adr-010-versioned-snapshots.md)
- [ADR-011: Statistical Gate for Edge Exposure](./adr-011-statistical-gate.md)
