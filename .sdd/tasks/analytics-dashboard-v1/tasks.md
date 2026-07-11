# Tasks: Analytics Dashboard v1.1.0

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

| Field | Value |
|-------|-------|
| Estimated changed lines | ~900-1000 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR #1 Backend (~450) → PR #2 Frontend (~450) |
| Delivery strategy | chained PRs, stacked-to-main |
| Chain strategy | stacked-to-main |

### Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend: schemas, calculators, 6 new endpoints, tests | PR #1 | Base: main. Independent deliverable. |
| 2 | Frontend: 7 hooks, 4 new components, DashboardPage extension, tests | PR #2 | Base: main. Only depends on API contracts, not PR #1 code. |

## Phase 1: Backend response models

- [ ] 1.1 Extend `schemas.py`: add `BreakdownItem`, `RDistributionResponse`, `RBucket`, `HeatmapCell`, `HeatmapResponse`; extend `SummaryResponse` with `total_trades_all`, `avg_r_multiple`, `gross_profit`, `gross_loss`
- [ ] 1.2 Add `mapped_field` helper for null→0 conversion on numeric fields in `schemas.py`

## Phase 2: Backend calculators

- [ ] 2.1 Extend `breakdown.py`: add `breakdown_by_strategy()`, `breakdown_by_setup()`, `breakdown_by_tags()`, `breakdown_by_mistakes()` — group by `id + name`, sort by `net_pnl DESC → trade_count DESC → name ASC`
- [ ] 2.2 Create `calculators/distribution.py`: `compute_r_distribution()` — bucket trades by risk multiple with `min_r`, `max_r`, `count`, `pnl`
- [ ] 2.3 Create `calculators/heatmap.py`: `compute_heatmap()` — aggregate by `day_of_week` (0-6) × `hour` (0-23) with `trade_count`, `net_pnl`

## Phase 3: Backend endpoints

- [ ] 3.1 Extend `TradeRepository.list_closed()` with optional `eager_load` param (`"strategy"`, `"setup"`, `"tags"`, `"mistakes"`) adding `selectinload`/`joinedload` options
- [ ] 3.2 Extend `AnalyticsService`: add `get_breakdown_strategies()`, `get_breakdown_setups()`, `get_breakdown_tags()`, `get_breakdown_mistakes()`, `get_distribution_r()`, `get_heatmap()` methods
- [ ] 3.3 Add 6 routes to `router.py`: `GET /analytics/breakdown/strategies`, `/setups`, `/tags`, `/mistakes`, `GET /analytics/distribution/r`, `GET /analytics/heatmap`

## Phase 4: Backend tests

- [ ] 4.1 Write calculator tests for `breakdown_by_strategy`, `by_setup`, `by_tags`, `by_mistakes` — empty, single-group, multi-group, null handling
- [ ] 4.2 Write calculator tests for `compute_r_distribution` — empty risk, single bucket, multi-bucket
- [ ] 4.3 Write calculator tests for `compute_heatmap` — single cell, multi-cell, empty
- [ ] 4.4 Write endpoint tests for all 6 new endpoints — 200 status, empty DB zeros, seeded values, OpenAPI schema

## Phase 5: Frontend API + hooks

- [ ] 5.1 Add 6 methods to `analyticsApi.js`: `getBreakdownStrategies`, `getBreakdownSetups`, `getBreakdownTags`, `getBreakdownMistakes`, `getRDistribution`, `getHeatmap`
- [ ] 5.2 Add 7 query keys to `constants.js` corresponding to cache keys from spec
- [ ] 5.3 Create 7 hooks in `hooks/`: `useBreakdownStrategies`, `useBreakdownSetups`, `useBreakdownTags`, `useBreakdownMistakes`, `useRDistribution`, `useHeatmap`, extend `useSummary` for new fields

## Phase 6: Frontend components

- [ ] 6.1 Extend `SummaryCards.jsx`: add Total Trades All and Avg R Multiple cards; expand grid from 5 to 7 cols
- [ ] 6.2 Create `BreakdownTable.jsx`: reusable table rendering `BreakdownItem[]` with loading/empty/error states, sortable by net_pnl
- [ ] 6.3 Create `RHistogram.jsx`: bar chart for R multiple buckets with count/pnl tooltips, loading/empty/error states
- [ ] 6.4 Create `HeatmapChart.jsx`: day×hour grid heatmap with color intensity by trade_count or net_pnl, loading/empty/error states

## Phase 7: Frontend integration

- [ ] 7.1 Extend `DashboardPage.jsx`: add 4 BreakdownTable instances (strategies, setups, tags, mistakes) in a responsive grid, add RHistogram section, add HeatmapChart section; wrap each in ErrorBoundary

## Phase 8: Frontend tests

- [ ] 8.1 Write component tests for `SummaryCards` — renders new Total Trades and Avg R cards
- [ ] 8.2 Write component tests for `BreakdownTable` — renders items, empty state, loading skeletons, error fallback
- [ ] 8.3 Write component tests for `RHistogram` — renders bars, empty "no risk data" state
- [ ] 8.4 Write component tests for `HeatmapChart` — renders grid cells, empty state

## AC Coverage Matrix

| AC | Task(s) | Verification |
|----|---------|--------------|
| AC-01: Summary exposes new fields | 1.1, 5.3, 6.1 | Schema + hook returns total_trades_all, avg_r_multiple, gross_profit, gross_loss |
| AC-02: 4 breakdown endpoints | 2.1, 3.2, 3.3, 4.1, 4.4 | 200 response with BreakdownItem[] sorted per spec |
| AC-03: Common BreakdownItem contract | 1.1 | Shared schema used by all 4 breakdown endpoints |
| AC-04: Sort order | 2.1 | net_pnl DESC → trade_count DESC → name ASC |
| AC-05: Null handling policy | 1.2, 2.1, 2.2, 2.3 | 0 for numerics, [] for arrays, None only when meaningful |
| AC-06: R distribution endpoint | 2.2, 3.2, 3.3, 4.2, 4.4 | Bucket contract with min_r, max_r, count, pnl |
| AC-07: Heatmap endpoint | 2.3, 3.2, 3.3, 4.3, 4.4 | Day×hour cells with trade_count, net_pnl |
| AC-08: Single query per endpoint | 3.2 | Service methods do one fetch → distribute to calculators |
| AC-09: No N+1 | 3.1 | Eager loading via selectinload for M:N relations |
| AC-10: Existing indexes sufficient | 2.1, 2.2, 2.3 | No new migrations; all group-by on FK columns already indexed |
