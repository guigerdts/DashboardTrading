# Delta for Risk Analytics

## Context

Calculators already exist in `calculators/exposure.py`, `calculators/correlation.py` and `calculators/risk.py`. This delta adds the wiring layer — response schemas, service methods, and router endpoints — with zero new metrics or calculators.

## ADDED Requirements

### Requirement: Response Schemas

The system MUST add Pydantic response models for risk analytics endpoints.

| Schema | Fields |
|--------|--------|
| `RiskMetricsResponse` | `max_consecutive_wins`, `max_consecutive_losses`, `avg_holding_time_hours`, `holding_time_distribution`, `avg_risk_per_trade`, `trades_without_risk`, `risk_utilization`, `kelly_fraction`, `kelly_disclaimer`, `risk_of_ruin`, `expectancy_adjusted` — all nullable except `kelly_disclaimer` |
| `ExposureItem` | `id`, `name`, `notional` (null for session/strategy), `trade_count`, `total_pnl` (by-asset only), `risk_total` (by-strategy only) |
| `ExposureResponse` | `items: list[ExposureItem]` |
| `CorrelationItem` | `asset_a`, `asset_b`, `pearson_r` (null if <30 shared trades), `trade_count` |
| `CorrelationResponse` | `items: list[CorrelationItem]` |

Degradation rules: empty collections → `[]`, uncomputable metrics → `null`, never 500 on partial data.

#### Scenario: Empty set returns empty list

- GIVEN no trades match filters
- WHEN any exposure or correlation endpoint returns
- THEN response contains `{"items": []}`

#### Scenario: Kelly disclaimer always present

- GIVEN any valid response from `risk-metrics`
- THEN `kelly_disclaimer` field MUST be a non-empty string stating the metric is informational only

### Requirement: Service Methods

The system MUST add 5 methods to `AnalyticsService` following the existing pattern: single `list_closed()` call → pipe through existing calculators → return Pydantic response.

| Method | Calculator(s) | Notes |
|--------|---------------|-------|
| `get_risk_metrics(filters, capital)` | `compute_performance`, `compute_streaks`, `compute_risk`, holding-time helpers | Takes optional `capital` param for RoR |
| `get_exposure_by_asset(filters)` | `compute_exposure_by_asset` | Uses `list_closed()` with no extra relations |
| `get_exposure_by_session(filters)` | `compute_exposure_by_session` | Groups by `market_session_id`, null → `"unknown"` |
| `get_exposure_by_strategy(filters)` | `compute_exposure_by_strategy` | Loads `strategy` relation |
| `get_correlation(filters)` | `compute_correlation` | Passes `min_trades=30` |

#### Scenario: Single query per method

- GIVEN each method is called
- THEN it calls `self.uow.trades.list_closed()` exactly once — verified by mock assertion

#### Scenario: Null degradation on uncomputable metrics

- GIVEN 0 closed trades
- WHEN `get_risk_metrics` returns
- THEN all optional fields (`avg_holding_time_hours`, `kelly_fraction`, etc.) are `null`, consecutive counts are 0

### Requirement: Router Endpoints

The system MUST add 5 endpoints to the analytics router under `/api/analytics/`.

| Endpoint | Method | Response Model |
|----------|--------|---------------|
| `/analytics/risk-metrics` | GET | `RiskMetricsResponse` |
| `/analytics/exposure/by-asset` | GET | `ExposureResponse` |
| `/analytics/exposure/by-session` | GET | `ExposureResponse` |
| `/analytics/exposure/by-strategy` | GET | `ExposureResponse` |
| `/analytics/exposure/correlation` | GET | `CorrelationResponse` |

Each endpoint MUST follow the existing pattern: `AnalyticsFilter` dependency → `get_analytics_service` DI → single service call.

#### Scenario: Mismatched capital type

- GIVEN `capital` query param is non-numeric
- WHEN `GET /analytics/risk-metrics?capital=abc`
- THEN FastAPI returns 422 with validation error

#### Scenario: Valid filter applied

- GIVEN `?account_id=1&date_from=2025-01-01` on any exposure endpoint
- THEN the service receives an `AnalyticsFilter` with those fields populated AND returns scoped data

### Requirement: Frontend Alignment

Existing React Query hooks (`useRiskMetrics`, `useExposureByAsset`, `useExposureBySession`, `useExposureByStrategy`, `useCorrelation`) in `frontend/src/modules/risk-management/hooks/` MUST work with the real endpoints without changes to hook or API service code.

#### Scenario: Hook returns typed response

- GIVEN real backend running
- WHEN `useRiskMetrics(10000)` resolves
- THEN `data` shape matches `RiskMetricsResponse` fields expected by `RiskMetricsCards`

#### Scenario: Error response propagates

- GIVEN backend returns 4xx/5xx
- THEN the hook's `isError` is `true` and `error` contains the server error message
