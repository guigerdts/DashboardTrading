# Design: v1.3.0 Risk Analytics

## Technical Approach

Nine new risk/probabilistic metrics + three exposure dimensions + cross-asset correlation, all computed in-memory from a single `list_closed()` call. Three new pure-function calculators in `calculators/`, three matching service methods, five endpoints, five frontend hooks, and a `RiskDashboard` composite. No schema changes, no new entities. Capital for Risk of Ruin accepted as query parameter (Account model has no `balance` field).

## Architecture Decisions

| Option | Tradeoffs | Decision |
|--------|-----------|----------|
| New calculators per file vs. monolithic `risk_analytics.py` | Single file reduces imports but violates single-responsibility; `exposure.py` and `correlation.py` are separate domains | **Three files** — `exposure.py`, `correlation.py`, extend `risk.py` with holding-time helpers |
| Capital source for RoR | Account model has no `balance` field; adding one requires migration | **Query param** `capital` on `/analytics/risk-metrics` — optional, nullable |
| Extend `AnalyticsService` vs. new `RiskAnalyticsService` | Existing service has 13 methods; adding risk-specific ones keeps cohesion | **Extend existing `AnalyticsService`** — same DI, same `list_closed` pattern |
| Open trade inclusion for exposure | `list_closed()` excludes open trades; exposure conceptually needs all | **`list_closed()` augmented with `status != "closed"` filter** — single query, all statuses |
| Correlation min threshold | Low threshold inflates noise; high excludes useful pairs | **30 trades per pair**, aligned with spec — return `null` below threshold |

## Data Flow

```
GET /analytics/risk-metrics?capital=10000
  │
  └─ AnalyticsService.get_risk_metrics(filters)
       ├── list_closed(filters, load_relations=["strategy"])
       ├── compute_performance(trades)         → win_rate, avg_win, avg_loss, expectancy
       ├── compute_streaks(trades)             → max_consecutive_wins/losses (reuse timeseries.py)
       ├── compute_holding_time_stats(trades)  → avg_holding_time_hours, distribution (NEW in risk.py)
       ├── compute_risk_per_trade(trades)      → avg_risk_per_trade, trades_without_risk (NEW in risk.py)
       ├── compute_kelly(win_rate, avg_win, avg_loss) → kelly_fraction
       ├── compute_risk_of_ruin(win_rate, profit_factor, capital, risk_per_trade) → risk_of_ruin
       └── compute_expectancy_adjusted(expectancy, pnl_std) → expectancy_adjusted

GET /analytics/exposure/by-asset
  └── AnalyticsService.get_exposure_by_asset(filters)
       └── compute_exposure_by_asset(trades)  → [{asset_id, notional, trade_count, total_pnl}]

GET /analytics/exposure/by-session
  └── AnalyticsService.get_exposure_by_session(filters)
       └── compute_exposure_by_session(trades) → [{session_id, trade_count}]

GET /analytics/exposure/by-strategy
  └── AnalyticsService.get_exposure_by_strategy(filters)  [load_relations=["strategy"]]
       └── compute_exposure_by_strategy(trades) → [{strategy_id, risk_total}]

GET /analytics/exposure/correlation
  └── AnalyticsService.get_correlation(filters)  [load_relations=["strategy"]]
       └── compute_correlation(trades, min_trades=30) → [{asset_a, asset_b, pearson_r, trade_count}]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/modules/analytics/calculators/exposure.py` | Create | `compute_exposure_by_asset`, `compute_exposure_by_session`, `compute_exposure_by_strategy` — pure, `list[Trade]` → `list[dict]` |
| `backend/app/modules/analytics/calculators/correlation.py` | Create | `compute_correlation(trades, min_trades=30)` — Pearson per asset pair, bail early for sparse |
| `backend/app/modules/analytics/calculators/risk.py` | Modify | Add `compute_holding_time_stats`, `compute_risk_per_trade`, `compute_risk_utilization`, `compute_kelly`, `compute_risk_of_ruin`, `compute_expectancy_adjusted` |
| `backend/app/modules/analytics/schemas.py` | Modify | Add `RiskMetricsResponse`, `ExposureItem`, `ExposureResponse`, `CorrelationItem`, `CorrelationResponse`, `KellyDisclaimer` models |
| `backend/app/modules/analytics/service.py` | Modify | Add 5 methods: `get_risk_metrics`, `get_exposure_by_asset`, `get_exposure_by_session`, `get_exposure_by_strategy`, `get_correlation` |
| `backend/app/modules/analytics/router.py` | Modify | Add 5 endpoints under `/api/analytics/` namespace |
| `frontend/src/modules/analytics/services/analyticsApi.js` | Modify | Add `getRiskMetrics`, `getExposureByAsset`, `getExposureBySession`, `getExposureByStrategy`, `getCorrelation` |
| `frontend/src/modules/analytics/utils/constants.js` | Modify | Add 5 query keys |
| `frontend/src/modules/risk-management/hooks/useRiskMetrics.js` | Create | `useQuery` wrapper for `analyticsApi.getRiskMetrics` |
| `frontend/src/modules/risk-management/hooks/useExposureByAsset.js` | Create | Hook for by-asset exposure |
| `frontend/src/modules/risk-management/hooks/useExposureBySession.js` | Create | Hook for by-session exposure |
| `frontend/src/modules/risk-management/hooks/useExposureByStrategy.js` | Create | Hook for by-strategy exposure |
| `frontend/src/modules/risk-management/hooks/useCorrelation.js` | Create | Hook for correlation matrix |
| `frontend/src/modules/risk-management/components/RiskDashboard.jsx` | Create | Composite: layout + state orchestration, delegates to sub-components |
| `frontend/src/modules/risk-management/components/RiskMetricsCards.jsx` | Create | Card grid for risk metrics |
| `frontend/src/modules/risk-management/components/ExposureTable.jsx` | Create | Reusable table for all 3 exposure dimensions |
| `frontend/src/modules/risk-management/components/CorrelationMatrix.jsx` | Create | Heatmap-style matrix for asset correlations |
| `frontend/src/modules/risk-management/services/riskAnalyticsApi.js` | Create | Thin bridge re-exporting from `analyticsApi` (or direct `api.get` calls) |
| `frontend/src/pages/RiskManagement.jsx` | Modify | Replace `ModuleTemplate` scaffold with `<RiskDashboard>` |

## Interfaces / Contracts

```python
# ── Response Schemas ──────────────────────────────────────────────

class RiskMetricsResponse(BaseModel):
    max_consecutive_wins: int      # 0 when no trades
    max_consecutive_losses: int    # 0 when no trades
    avg_holding_time_hours: float | None  # null if 0 trades
    holding_time_distribution: dict[str, int]  # {"<1h": N, "1-4h": N, ...}
    avg_risk_per_trade: float | None  # null if no risk_amount
    trades_without_risk: int      # count of trades with null/0 risk_amount
    risk_utilization: float | None  # percentage, null if no data
    kelly_fraction: float | None  # null if insufficient data
    kelly_disclaimer: str         # always present
    risk_of_ruin: float | None    # null if no capital or no risk data
    expectancy_adjusted: float | None  # null if < 2 trades

class ExposureItem(BaseModel):
    id: int | str                 # asset_id / session_id / strategy_id
    name: str                     # resolved name or "unknown"
    notional: float | None = None # by-asset only
    trade_count: int
    total_pnl: float | None = None  # by-asset only
    risk_total: float | None = None # by-strategy only

class ExposureResponse(BaseModel):
    items: list[ExposureItem]

class CorrelationItem(BaseModel):
    asset_a: str
    asset_b: str
    pearson_r: float | None       # null if < 30 trades
    trade_count: int

class CorrelationResponse(BaseModel):
    items: list[CorrelationItem]
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (calc) | Each new calculator metric — empty, single, normal, edge | Pure function assertions: known input → expected output |
| Service (int) | Each service method delegates to `list_closed` once + calculator piping | Mocked `UnitOfWork.trades.list_closed`, assert response shape |
| Router (int) | 200 with data, 422 on invalid filter, empty/single/partial | `TestClient`, assert status + response model |
| Component | Loading skeleton, error retry, empty state, success render | `vitest` + `@testing-library/react` |
| Hook | Query key shape, API call delegation | `vitest` spying on `analyticsApi` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

No migration required. New endpoints are additive — existing `risk-metrics` output is a superset of current `RiskMetrics`. Frontend page remains scaffold until the PR rolls out.

## Open Questions

- [ ] `risk_management` backend module (placeholder router) — leave as-is or wire into this change?
- [ ] Should exposure endpoints share a single `list_all` (open+closed) call or does service need a new repository method?
