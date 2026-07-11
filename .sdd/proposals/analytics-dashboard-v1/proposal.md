# Proposal: Analytics Dashboard v1.1.0

## Intent

Trade data already exists with rich dimensions (strategy, setup, tags, mistakes) and computed metrics (monthly PnL, avg_r_multiple, gross P&L) — but no dashboard exposes them. Users must inspect individual trades to see patterns. This change builds a read-only analytics dashboard aggregating KPIs, breakdowns, and distributions.

## Scope

### In Scope
- 4 new fields on `GET /analytics/summary`: total_trades_all, avg_r_multiple, gross_profit, gross_loss
- 6 new read-only endpoints: breakdown/strategies, breakdown/setups, breakdown/tags, breakdown/mistakes, distribution/r, heatmap
- 7 KPI cards (Total Trades, Win Rate, Net PnL, Profit Factor, Expectancy, Average R, Max Drawdown), Monthly PnL bar chart, equity curve (reuse), R histogram, Day×Hour heatmap
- Strategy, Setup, Tag, Mistake breakdown tables
- Aggregated endpoints — one call returns multiple blocks where feasible

### Out of Scope
IA, insights, rankings, period comparison, benchmarking, exports, ML, new entities, schema changes

## Capabilities

### New Capabilities
- `analytics-breakdowns`: per-dimension trade performance by strategy, setup, tag, mistake
- `analytics-distributions`: R-multiple histogram and weekday×hour heatmap
- `dashboard-analytics-kpis`: extended KPI cards (7 cards from extended summary + existing equity curve)

### Modified Capabilities
- None at spec level — existing endpoints extend response shape only

## Approach

Extend the existing analytics module — no new entities, no schema changes. Each endpoint follows the existing pattern: `list_closed()` query → pure-function calculator in memory. Strategy/setup breakdowns use FK group-by (like asset/direction). Tag/mistake need M:N/1:N flatten via the pivot tables (trade_tags, mistake_entries). Summary endpoint reuses already-computed `PerformanceMetrics` fields. Frontend reuses `DashboardPage`, `SummaryCards`, `FiltersBar`, `EquityChart`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/modules/analytics/schemas.py` | Modified | Extend SummaryResponse |
| `backend/app/modules/analytics/router.py` | Modified | +6 routes |
| `backend/app/modules/analytics/service.py` | Modified | +6 methods |
| `backend/app/modules/analytics/calculators/` | Modified | +breakdown/distribution calculators |
| `backend/app/modules/trades/repository.py` | Modified | Extend list_closed() eager-loads |
| `frontend/…/services/analyticsApi.js` | Modified | +6 API methods |
| `frontend/…/hooks/` | Modified | +6 query hooks |
| `frontend/…/components/` | Modified | KPI cards, heatmap, histogram |
| `frontend/…/pages/DashboardPage.jsx` | Modified | Wire new blocks |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Aggregated endpoint returns too much data at scale | Low | Benchmarked at O(10k); paginate only at O(100k+) |
| Tag/mistake M:N joins degrade performance | Low | Eager-load with selectinload; test with realistic data |
| list_closed() needs broader eager-loads | Low | Extend options param with defaults |

## Rollback Plan

Revert 4 summary fields from schema/response; remove 6 routes from router.py; revert list_closed() eager-loads. No DB migrations — no schema changes.

## Success Criteria

- [ ] All 7 KPI cards render correct values matching raw trade data
- [ ] Each breakdown endpoint returns correct per-group metrics
- [ ] R histogram buckets match computed R-multiple distribution
- [ ] Heatmap cells show correct PnL/count per weekday×hour
- [ ] All existing analytics tests pass unchanged
- [ ] New endpoints have unit + integration tests
