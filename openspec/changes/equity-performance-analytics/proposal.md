# Proposal: v1.2.0 — Equity & Performance Analytics

## Intent

Build Equity & Performance Analytics without modifying the DB schema, reusing existing analytics infrastructure.

## Scope

### In Scope

**Backend**
| Deliverable | Detail |
|-------------|--------|
| `calculators/rolling.py` | Sliding-window: Win Rate, Profit Factor, Expectancy, Avg R. Default 30 trades, configurable via `window_size` |
| `calculators/timeseries.py` | Add quarterly + yearly grouping to existing daily/weekly/monthly |
| `GET /analytics/rolling` | Rolling performance metrics |
| `GET /analytics/performance/by-period` | Metrics grouped by month/quarter/year |
| `GET /analytics/performance/compare` | Compare two arbitrary date ranges |
| `AnalyticsService` | 3 new service methods |
| `AnalyticsFilter` | Add optional `window_size` |

**Frontend**
| Deliverable | Detail |
|-------------|--------|
| `analyticsApi.getPerformance()` | Replace stub with real API call |
| `buildParams` | Add `windowSize` |
| Hooks | `useRollingMetrics`, `usePerformanceByPeriod`, `usePerformanceComparison` |
| Components | `RollingMetricsChart`, `PerformanceByPeriod`, `PeriodComparison` |
| `QUERY_KEYS` | New query key entries |
| `DashboardPage` | Wire new components in |

### Out of Scope
AI/predictions, Monte Carlo, Risk of Ruin, MAE/MFE, exports (CSV/Excel), benchmark against indices, advanced statistical optimization.

## Capabilities

### New
- `equity-performance-analytics`: Rolling metrics, period-grouped performance, date-range comparison. Backend calculators + endpoints + frontend hooks/components.

### Modified
None — additive within analytics module, no existing spec changes.

## Approach

Pure additive change. All patterns follow v1.1 exactly:
- **Calculators**: pure functions (existing pattern)
- **Rolling window**: 30 trades configurable via `window_size`
- **Filters**: reuse `useDashboardFilters`
- **Zero migrations, zero new entities/models, zero new dependencies, zero duplicated aggregation logic**

Only existing files touched: `timeseries.py`, `calculators/__init__.py`, `schemas.py`, `service.py`, `router.py`, `analyticsApi.js`, `buildParams.js`, `QUERY_KEYS.js`, `DashboardPage.jsx`.

## Affected Areas

| Area | Impact |
|------|--------|
| `calculators/rolling.py` | New |
| `calculators/timeseries.py` | Modified |
| `calculators/__init__.py` | Modified |
| `schemas.py` | Modified |
| `service.py` | Modified |
| `router.py` | Modified |
| `services/analyticsApi.js` | Modified |
| `services/buildParams.js` | Modified |
| `hooks/` (3 files) | New |
| `components/` (3 files) | New |
| `QUERY_KEYS.js` | Modified |
| `DashboardPage.jsx` | Modified |

All paths under `backend/app/modules/analytics/` or `frontend/src/modules/analytics/`.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Rolling calc perf on large trade sets | Low | In-memory on fetched trades. Paginate `list_closed()` if needed. |
| Window size not in filter chain | Low | Additive field — `None` = default 30. |

## Rollback Plan

Revert the commit. No migrations, no schema changes, no data affected.

## Dependencies

Existing analytics infrastructure (trade model, calculators, equity endpoint). No new packages.

## Success Criteria

- [ ] All tests pass (backend + frontend) with no regressions
- [ ] Rolling metrics match manual calc for sample data
- [ ] Period comparison shows correct abs and % diffs
- [ ] "Insufficient data" renders for windows below minimum threshold
- [ ] Zero schema migrations created
