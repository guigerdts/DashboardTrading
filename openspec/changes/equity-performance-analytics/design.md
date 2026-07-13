# Design: v1.2.0 Equity & Performance Analytics

## Technical Approach

Pure additive extension of the analytics module. Three new calculator functions across two files → three service methods → three endpoints → three React Query hooks → three presentational components. Every endpoint fetches trades once via `list_closed()` and distributes to pure calculators. Zero schema changes, zero new dependencies.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|-------------|-----------|
| AD-1: Rolling window | Pure function `compute_rolling_metrics(trades, window_size)` in `rolling.py` | Service-level loop, SQL window function | Follows existing `performance.py`/`risk.py` pattern. Testable without FastAPI/DB |
| AD-2: Period grouping | Extend `timeseries.py` with `compute_performance_by_period()` | New dedicated file | Groups by date key, passes each group to existing `compute_performance()`. Zero duplication |
| AD-3: Service orchestration | 3 new methods, each `list_closed()` → filter → calculator | Per-endpoint calculator imports | Matches existing `get_equity()` / `get_performance()` pattern exactly |
| AD-4: Compare deltas | Server computes delta + delta_percent from shared fields | Client-side math | Spec mandate. `delta_percent` is `null` when base field is 0 |
| AD-5: Frontend decoupling | 3 hooks (React Query + URL filters) + 3 presentational components | Monolithic hook, stateful components | Follows `EquityChart` / `useEquity` pattern exactly |
| AD-6: Chart reuse | Reuse existing Recharts config (`EquityChart.jsx` — ResponsiveContainer, grid, tooltip, CHART_COLORS) | New chart configs | Single source of truth for axis formatters and color scheme |
| AD-7: Window size on filter | `window_size` on `AnalyticsFilter` (backend) and `buildParams` (frontend) | Separate query param | Consistent with existing param chain. Default 30, validated 10–200 |

## Data Flow

```
DashboardPage
  ├── useRollingMetrics(filters) ──→ analyticsApi.getRolling(params)
  ├── usePerformanceByPeriod(filters, period) ──→ analyticsApi.getPerformanceByPeriod(params)
  └── usePerformanceComparison(filters, pA, pB) ──→ analyticsApi.comparePeriods(params)

AnalyticsService (1×list_closed per method)
  ├── rolling.py ──→ compute_rolling_metrics(trades, window_size)
  ├── timeseries.py ──→ compute_performance_by_period(trades, group_by)
  └── risk.py ──→ compute_risk(trades) [reused for drawdown in PeriodComparison]
```

## Key Patterns (Non-obvious)

**Sliding window** (`rolling.py`) — O(n) over sorted trades, calls `compute_performance()` per window:

```python
def compute_rolling_metrics(trades: list[Trade], window_size: int = 30) -> list[dict]:
    if len(trades) < window_size:
        return []  # spec: empty array, not null
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or t.entry_datetime)
    points = []
    for i in range(window_size - 1, len(sorted_trades)):
        window = sorted_trades[i - window_size + 1 : i + 1]
        perf = compute_performance(window)
        points.append(dict(index=i - window_size + 2, trade_count=window_size, **perf))
    return points
```

**Period grouping** (timeseries.py — new function, not extending `compute_pnl_by_period` since spec needs full metrics):

```python
def compute_performance_by_period(trades, group_by="month"):
    groups: dict[str, list[Trade]] = defaultdict(list)
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or t.entry_datetime)
    for t in sorted_trades:
        dt = _to_dt(t.exit_datetime or t.entry_datetime)
        match group_by:
            case "quarter": key = f"{dt.year}-Q{(dt.month-1)//3+1}"
            case "year":    key = str(dt.year)
            case _:         key = dt.strftime("%Y-%m")
        groups[key].append(t)
    return [{"period": k, **compute_performance(v)} for k, v in sorted(groups.items())]
```

**Compare delta** — dict subtraction over shared metric fields (`net_pnl`, `gross_profit`, `win_rate`, etc.), nulling `profit_factor`/`avg_r_multiple` when denominator is 0.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `calculators/rolling.py` | Create | Sliding-window metrics: win rate, PF, expectancy, avg R |
| `calculators/timeseries.py` | Modify | Add `compute_performance_by_period(trades, group_by)` — quarter/year/month |
| `schemas.py` | Modify | Add `RollingPoint`, `RollingResponse`, `PeriodPerformanceRecord`, `PeriodComparisonResponse` + `window_size` on `AnalyticsFilter` |
| `service.py` | Modify | 3 new methods: `get_rolling`, `get_performance_by_period`, `get_performance_compare` |
| `router.py` | Modify | 3 new endpoints: `GET /rolling`, `GET /performance/by-period`, `GET /performance/compare` |
| `analyticsApi.js` | Modify | 3 new methods + `windowSize` in `buildParams`; replace `getPerformance` stub |
| `constants.js` | Modify | 3 new query key factories: `rolling`, `performanceByPeriod`, `performanceCompare` |
| `useRollingMetrics.js` | Create | Hook → `['analytics', 'rolling', filters]` |
| `usePerformanceByPeriod.js` | Create | Hook → `['analytics', 'performance', period, filters]` |
| `usePerformanceComparison.js` | Create | Hook → `['analytics', 'compare', filters]` |
| `RollingMetricsChart.jsx` | Create | Recharts LineChart — win_rate + expectancy lines over index |
| `PerformanceByPeriod.jsx` | Create | Table of period records |
| `PeriodComparison.jsx` | Create | Side-by-side period A vs B with delta columns |
| `DashboardPage.jsx` | Modify | Import + wire 3 new hooks/components after HeatmapChart |

## Interfaces (Schemas)

```python
class RollingPoint(BaseModel):
    index: int
    win_rate: float
    profit_factor: float | None = None
    expectancy: float
    avg_r_multiple: float | None = None
    trade_count: int

class RollingResponse(BaseModel):
    window_size: int
    points: list[RollingPoint]

class PeriodPerformanceRecord(BaseModel):
    period: str
    trade_count: int
    net_pnl: float
    gross_profit: float
    gross_loss: float
    win_rate: float
    profit_factor: float | None = None
    expectancy: float
    avg_r_multiple: float | None = None

class PeriodComparisonResponse(BaseModel):
    period_a: PeriodPerformanceRecord
    period_b: PeriodPerformanceRecord
    delta: PeriodPerformanceRecord
    delta_percent: PeriodPerformanceRecord
```

React Query keys:
```
['analytics', 'rolling', filters]
['analytics', 'performance', period, filters]
['analytics', 'compare', filters]
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit (calculator) | `rolling.py`, `compute_performance_by_period` | Pure function — fixture trade list in → assert dict out. Test insufficient trades, quarter boundaries, empty groups |
| Integration (service) | 3 new service methods | Mock `TradeRepository.list_closed()` — verify single call, correct calculator dispatch |
| Endpoint (router) | 3 new routes | TestClient — validate 200 (normal), 422 (invalid window_size), empty-state 200 with `[]` |
| Component | RollingMetricsChart, PerformanceByPeriod, PeriodComparison | vitest + Testing Library — render with fixture data; test loading/empty/error states |
| Hook | useRollingMetrics, usePerformanceByPeriod, usePerformanceComparison | vitest — verify query key shape and API delegation |

## Threat Matrix

N/A — no routing (URL path prefix unchanged), shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. All changes are additive within the analytics module.

## Migration / Rollout

No migration required. Zero schema changes. Rollback is a single commit revert.

## Open Questions

None. All design decisions resolved in the exploration and proposal phases.
