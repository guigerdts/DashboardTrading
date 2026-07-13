# Tasks: v1.3.0 Risk Analytics

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~450-550 per PR |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR #1 Backend → PR #2 Frontend |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Backend: calculators + service + router + tests | PR 1 | `python -m pytest tests/modules/analytics/ -k "risk or exposure or correlation"` | `pytest` with mocked `list_closed` | Revert new calculators, service methods, endpoints, schemas |
| 2 | Frontend: hooks + components + RiskDashboard + wiring | PR 2 | `npx vitest run --pool=threads src/modules/risk-management/` | `vitest` with mocked API layer | Revert risk-management module additions + page change |

## Phase 1: Calculators — Backend

- [ ] 1.1 `risk.py` — `compute_holding_time_stats(trades)`: avg_holding_time_hours + distribution buckets. Skip null exit_datetime.
- [ ] 1.2 `risk.py` — `compute_risk_per_trade(trades)`: avg_risk_per_trade + trades_without_risk counter.
- [ ] 1.3 `risk.py` — `compute_risk_utilization(trades)`: avg(risk_amount / (pos_size * entry_price)). Skip null entries.
- [ ] 1.4 `risk.py` — `compute_kelly(wr, avg_win, avg_loss)`: kelly_fraction per formula. Null if insufficient data.
- [ ] 1.5 `risk.py` — `compute_risk_of_ruin(wr, pf, capital, risk_per_trade)`. Null if capital missing or wr≤0.
- [ ] 1.6 `risk.py` — `compute_expectancy_adjusted(expectancy, pnl_values)`: expectancy / std(pnl). Null if <2 trades.
- [ ] 1.7 Create `exposure.py` — `compute_exposure_by_asset(trades)`: notional (pos_size × entry_price), trade_count, total_pnl per asset. Closed trades only.
- [ ] 1.8 `exposure.py` — `compute_exposure_by_session(trades)`: trade_count grouped by market_session_id. Null → "unknown". Closed only.
- [ ] 1.9 `exposure.py` — `compute_exposure_by_strategy(trades)`: sum risk_amount + trade_count per strategy_id. Closed only.
- [ ] 1.10 Create `correlation.py` — `compute_correlation(trades, min_trades=30)`: Pearson per asset pair. Exclude pairs <30 → null.
- [ ] 1.11 Unit tests — all new calculators: empty, single trade, all wins/losses, null fields, sparse data.

## Phase 2: Schemas + Service + Router — Backend

- [ ] 2.1 Add schemas: `RiskMetricsResponse`, `ExposureItem`, `ExposureResponse`, `CorrelationItem`, `CorrelationResponse` with degradation-safe nulls.
- [ ] 2.2 `service.py` — `get_risk_metrics(filters)`: single `list_closed`, pipe through all calculators, apply null-degradation rule.
- [ ] 2.3 `service.py` — `get_exposure_by_asset`, `get_exposure_by_session`, `get_exposure_by_strategy`, `get_correlation`.
- [ ] 2.4 `router.py` — 5 endpoints: `GET /analytics/risk-metrics`, `/analytics/exposure/by-asset`, `/by-session`, `/by-strategy`, `/exposure/correlation`.
- [ ] 2.5 Integration tests — service + router: 200 with data, 422 invalid filter, empty/single/partial edge cases.

## Phase 3: API + Hooks — Frontend

- [ ] 3.1 Create `risk-management/services/riskAnalyticsApi.js` — 5 API methods following existing `analyticsApi` patterns.
- [ ] 3.2 Create `hooks/useRiskMetrics.js` — React Query wrapper, key `['analytics', 'risk-metrics', filters]`.
- [ ] 3.3 Create `hooks/useExposureByAsset.js` — key `['analytics', 'exposure', 'by-asset', filters]`.
- [ ] 3.4 Create `hooks/useExposureBySession.js`, `useExposureByStrategy.js`, `useCorrelation.js`.

## Phase 4: Components + Wiring — Frontend

- [ ] 4.1 Create `RiskMetricsCards.jsx` — card grid: holding time, risk/trade, Kelly, RoR, expectancy-adj.
- [ ] 4.2 Create `ExposureTable.jsx` — reusable table for asset/session/strategy dimensions.
- [ ] 4.3 Create `CorrelationMatrix.jsx` — heatmap-style grid for asset pair correlations.
- [ ] 4.4 Create `RiskDashboard.jsx` — composite: fetches all hooks, renders 3 child components.
- [ ] 4.5 Update `RiskManagement.jsx` — replace ModuleTemplate scaffold with `<RiskDashboard>`.
- [ ] 4.6 Component + hook tests — loading/error/empty/success states for all 5 components.

## Phase 5: Verify

- [ ] 5.1 `cd frontend && npm run lint` — 0 errors.
- [ ] 5.2 `cd frontend && npx vitest run && cd ../backend && python -m pytest` — all pass.
- [ ] 5.3 `cd frontend && npm run build` — clean.
