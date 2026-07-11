# Design: Analytics Dashboard v1.1.0

## Technical Approach

Extend the existing analytics module following its established pattern: single fetch of closed trades via `list_closed()`, eager-load required relationships (strategy, setup, tags, mistakes), then compute derived metrics in pure calculator functions. No DB schema changes. Six new endpoints + summary extension, all read-only. Frontend adds 6 hooks, 3 new components, and extends DashboardPage.

## Architecture Decisions

### Decision: In-memory computation over SQL aggregation

| Option | Tradeoff | Decision |
|--------|----------|----------|
| SQL GROUP BY with PnL expressed as CASE + arithmetic | Complex, duplicates business logic in SQL. Tags/mistakes need M:N subqueries. | Rejected |
| Load trades + group/compute in Python | Matches existing `breakdown_by_asset/direction/market` pattern exactly. `compute_performance` is shared. O(n) per dimension. Acceptable for O(10k) trades. | **Chosen** |

### Decision: Extend `list_closed()` with optional eager loading

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Always load strategy/setup/tags/mistakes | Penalizes existing callers with unnecessary joins | Rejected |
| Add `eager_load: list[str]` parameter | Minimal change, backward compatible | **Chosen** |

### Decision: Single reusable `BreakdownTable` component

All 4 breakdown endpoints (`/strategies`, `/setups`, `/tags`, `/mistakes`) return `{ items: [...] }` with identical shape per the common breakdown contract. One component renders all 4, configured by `title` and `columns` props. Saves ~200 lines vs 4 separate components.

### Decision: Summary extension fields only — no breaking changes

`avg_r_multiple` already in `PerformanceMetrics`. Monthly PnL appended as `monthly_pnl: list[PnLPeriod]`. Existing frontend ignores unknown fields.

## Data Flow

```
Browser → DashboardPage
  ├── useSummary()           → GET /api/analytics/summary
  ├── useStrategyBreakdown() → GET /api/analytics/breakdown/strategies
  ├── useSetupBreakdown()    → GET /api/analytics/breakdown/setups
  ├── useTagBreakdown()      → GET /api/analytics/breakdown/tags
  ├── useMistakeBreakdown()  → GET /api/analytics/breakdown/mistakes
  ├── useRDistribution()     → GET /api/analytics/distribution/r
  └── useHeatmap()           → GET /api/analytics/heatmap

Backend per endpoint:
  list_closed(eager_load=[...]) → trades[]
    → calculator function (pure) → response schema via service method
```

## Interfaces / Contracts

**Summary extension** — backward compatible:
```python
class SummaryResponse(BaseModel):
    total_trades: int
    performance: PerformanceMetrics   # already has avg_r_multiple
    risk: RiskMetrics
    monthly_pnl: list[PnLPeriod] = [] # NEW
```

**Common breakdown** (strategies, setups, tags, mistakes):
```python
class BreakdownEntry(BaseModel):
    name: str
    trade_count: int
    net_pnl: float
    win_rate: float
    profit_factor: float | None = None
    expectancy: float

class BreakdownResponse(BaseModel):
    total_trades: int
    items: list[BreakdownEntry]       # sorted by backend
```

**R Distribution**:
```python
class RDistributionItem(BaseModel):   # { "bucket": "-2", "count": 3 }
    bucket: str
    count: int

class RDistributionResponse(BaseModel):
    total_trades: int
    buckets: list[RDistributionItem]  # empty if no trades have risk_amount
```

**Heatmap**:
```python
class HeatmapItem(BaseModel):         # { "day": 1, "hour": 9, "trade_count": 14, "net_pnl": 325.5 }
    day: int                           # 0=Monday
    hour: int                          # 0-23
    trade_count: int
    net_pnl: float

class HeatmapResponse(BaseModel):
    total_trades: int
    cells: list[HeatmapItem]          # empty cells omitted
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/modules/trades/repository.py` | Modify | Extend `list_closed()` with optional `eager_load` param. Add `joinedload` for strategy, setup; `selectinload` for tags, mistakes. |
| `backend/app/modules/analytics/schemas.py` | Modify | Add `BreakdownEntry`, `BreakdownResponse`, `RDistributionItem`, `RDistributionResponse`, `HeatmapItem`, `HeatmapResponse`. Extend `SummaryResponse` with `monthly_pnl`. |
| `backend/app/modules/analytics/calculators/breakdown.py` | Modify | Add 4 functions: `by_strategy`, `by_setup`, `by_tags`, `by_mistakes`. Each groups trades by FK or junction, calls `compute_performance` per group, returns sorted list by net_pnl DESC → trade_count DESC → name ASC. |
| `backend/app/modules/analytics/calculators/distribution.py` | Create | `compute_r_distribution(trades)` — compute R = PnL/risk_amount per trade with risk_amount > 0, bucket into 6 ranges: "< -2", "-2 to -1", "-1 to 0", "0 to 1", "1 to 2", "2+". Empty array if no trades have risk_amount. |
| `backend/app/modules/analytics/calculators/heatmap.py` | Create | `compute_heatmap(trades)` — extract weekday 0-6 and hour 0-23 from `exit_datetime`, aggregate by (day, hour), return cells with trade_count and net_pnl. |
| `backend/app/modules/analytics/service.py` | Modify | Add 6 new methods + extend `get_summary` with monthly PnL computation. |
| `backend/app/modules/analytics/router.py` | Modify | Add 6 endpoints: `/breakdown/strategies`, `/breakdown/setups`, `/breakdown/tags`, `/breakdown/mistakes`, `/distribution/r`, `/heatmap`. Same pattern as existing. |
| `frontend/src/modules/analytics/utils/constants.js` | Modify | Add 6 `QUERY_KEYS` entries: `strategyBreakdown`, `setupBreakdown`, `tagBreakdown`, `mistakeBreakdown`, `rDistribution`, `heatmap`. |
| `frontend/src/modules/analytics/services/analyticsApi.js` | Modify | Add 6 API methods following existing pattern. |
| `frontend/src/modules/analytics/hooks/useStrategyBreakdown.js` | Create | Pattern from `useAssetBreakdown.js` — `useQuery` with key `['analytics', 'breakdown', 'strategies', filters]`. |
| `frontend/src/modules/analytics/hooks/useSetupBreakdown.js` | Create | Same pattern, key `['analytics', 'breakdown', 'setups', filters]`. |
| `frontend/src/modules/analytics/hooks/useTagBreakdown.js` | Create | Same pattern, key `['analytics', 'breakdown', 'tags', filters]`. |
| `frontend/src/modules/analytics/hooks/useMistakeBreakdown.js` | Create | Same pattern, key `['analytics', 'breakdown', 'mistakes', filters]`. |
| `frontend/src/modules/analytics/hooks/useRDistribution.js` | Create | Same pattern, key `['analytics', 'distribution', 'r', filters]`. |
| `frontend/src/modules/analytics/hooks/useHeatmap.js` | Create | Same pattern, key `['analytics', 'heatmap', filters]`. |
| `frontend/src/modules/analytics/components/BreakdownTable.jsx` | Create | Reusable table — reads `data.items[]`, renders columns for name/net_pnl/win_rate/trade_count/profit_factor/expectancy. Handles loading/empty/error states. Sorted by backend — no client sort. |
| `frontend/src/modules/analytics/components/RDistributionChart.jsx` | Create | Horizontal bar chart (CSS or Recharts). Bucket labels on Y, count on X. Empty state when buckets = []. |
| `frontend/src/modules/analytics/components/HeatmapChart.jsx` | Create | 7×24 grid. Day rows, hour columns. Cell color intensity by trade_count. Empty cells from data, fill missing with zero in render. |
| `frontend/src/modules/analytics/pages/DashboardPage.jsx` | Modify | Import 6 new hooks + 3 new components + 4 `<BreakdownTable>` instances. Add to layout below existing 2-column breakdowns, in a 2x2 grid or single column. |

## React Query Configuration

All new hooks use `staleTime: 5 * 60 * 1000` (300,000ms). No cache invalidation — read-only data. Queries refetch only on filter change (key change) or page reload. `staleTime` prevents refetch on tab focus.

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit — calculators | `distribution.py` edge cases: zero trades, null risk_amount, single trade, all same bucket | Pure function tests per existing pattern |
| Unit — calculators | `breakdown.py` new functions: strategy/setup grouping, tag/mistake M:N grouping | Fixture trades with known relationships |
| Unit — calculators | `heatmap.py`: weekday/hour extraction, aggregation, empty period | Trade list with known exit_datetimes |
| Integration | All 7 endpoint response shapes via FastAPI TestClient | Filters applied, contract verified per spec |
| Frontend — hooks | Each hook response shape with mock | Loading → success → error transitions |
| Frontend — components | BreakdownTable + RDistributionChart + HeatmapChart | Fixture data, empty, error states |

## Delivery Recommendation

**Single PR**. ~350 lines backend (service + schemas + 2 new calculators + repository extension). ~450 lines frontend (6 hooks + 3 components + DashboardPage extension). ~800 total. All additive, no breaking changes, existing patterns are well-established. Stacked PRs only if tooling enforces a 400-line review limit.
