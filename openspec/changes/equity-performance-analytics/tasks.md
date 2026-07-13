# Tasks: v1.2.0 — Equity & Performance Analytics

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 450–550 per PR |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Backend) → PR 2 (Frontend) |
| Delivery strategy | ask-on-risk |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Backend: calc + service + routes + tests | PR 1 | `cd backend && python -m pytest tests/modules/analytics/ -v` | `curl localhost:8000/api/v1/analytics/rolling?window_size=30` | Revert PR #1 commit |
| 2 | Frontend: hooks + components + wiring + tests | PR 2 | `cd frontend && npx vitest run modules/analytics/` | Dashboard page manual load | Revert PR #2 commit |

## Phase 1: PR #1 — Backend

- [ ] 1.1 Create `calculators/rolling.py` — pure `compute_rolling_metrics()`; insufficient-trades → `[]` guard
- [ ] 1.2 Extend `calculators/timeseries.py` — add `compute_performance_by_period()` with month/quarter/year grouping, null PF for all-wins
- [ ] 1.3 Extend `schemas.py` — response DTOs (`RollingPoint`, `RollingResponse`, `PeriodPerformanceRecord`, `PeriodComparisonResponse`) + `window_size` on `AnalyticsFilter`
- [ ] 1.4 Extend `service.py` — 3 methods, each `list_closed()` once, dispatch to calculators, compute compare deltas (null when base is 0)
- [ ] 1.5 Extend `router.py` — 3 endpoints: `GET /rolling`, `GET /performance/by-period`, `GET /performance/compare`
- [ ] 1.6 Test: calculator units — rolling edge cases (insufficient trades, all-wins, zero drawdown) + period grouping (quarter boundaries, empty periods)
- [ ] 1.7 Test: service integration — mock `list_closed()`, verify single-call + correct dispatch per method
- [ ] 1.8 Test: router — 200 with data, 422 invalid `window_size`, 200 with empty `points`
- [ ] 1.9 Verify: `ruff check . && python -m pytest --cov`

## Phase 2: PR #2 — Frontend

- [ ] 2.1 Extend `analyticsApi.js` — 3 API methods; add `windowSize` to `buildParams`; replace `getPerformance` stub
- [ ] 2.2 Extend `QUERY_KEYS` — factories: `rolling(filters)`, `performanceByPeriod(period, filters)`, `compare(filters)`
- [ ] 2.3 Create `useRollingMetrics.js` — React Query hook, key `['analytics', 'rolling', filters]`
- [ ] 2.4 Create `usePerformanceByPeriod.js` — React Query hook, key `['analytics', 'performance', period, filters]`
- [ ] 2.5 Create `usePerformanceComparison.js` — React Query hook, key `['analytics', 'compare', filters]`
- [ ] 2.6 Create `RollingMetricsChart.jsx` — Recharts LineChart, win_rate + expectancy over index
- [ ] 2.7 Create `PerformanceByPeriod.jsx` — table of period records
- [ ] 2.8 Create `PeriodComparison.jsx` — side-by-side A vs B with delta + delta_percent columns
- [ ] 2.9 Wire new components into `DashboardPage.jsx` after HeatmapChart
- [ ] 2.10 Test: hooks — query key shape + API delegation via vitest
- [ ] 2.11 Test: components — render with fixture data; cover loading/empty/error/success
- [ ] 2.12 Verify: `npx eslint . && npx vitest run && npm run build`
