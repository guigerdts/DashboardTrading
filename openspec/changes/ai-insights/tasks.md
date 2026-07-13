# Tasks: AI Insights v1.5.0

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

Estimated ~1,700 LOC across 4 stacked PRs: #1 risk-analytics (~400), #2 engine+schemas (~450), #3 API (~350), #4 frontend (~500).

| Unit | PR | Focused test | Harness | Rollback |
|------|----|-------------|---------|----------|
| Risk Analytics | #1 | `pytest tests/modules/analytics/ -v` | `GET /api/analytics/risk-metrics` | 5 files |
| Engine+Schemas | #2 | `pytest tests/modules/ai_insights/ -v -k "not integration"` | `RuleEngine.evaluate(fixture)` | `ai_insights/` dir |
| API Layer | #3 | `pytest tests/modules/ai_insights/ -v -k integration` | `GET /api/ai-insights/summary` | `router.py` + test |
| Frontend | #4 | `vitest run modules/ai-insights/` | `/analytics/insights` mock | module + route |

## Phase 1: Risk Analytics (PR#1) — P1, ~400 LOC

- [ ] 1.1 Add `RiskMetricsResponse`, `Exposure*Schema`, `CorrelationItem` to `analytics/schemas.py`
- [ ] 1.2 Add `_compute_holding_time/kelly/ror` helpers to `analytics/calculators/risk.py`
- [ ] 1.3 Add 5 service methods to `analytics/service.py`: `get_risk_metrics`, `get_exposure_by_asset|session|strategy`, `get_correlation`
- [ ] 1.4 Add 5 routes to `analytics/router.py`: `/risk-metrics`, `/exposure/by-asset|session|strategy`, `/correlation`
- [ ] 1.5 Service tests: mock uow, assert response shape in `test_service.py`
- [ ] 1.6 Integration tests: httpx, seeded trades, empty DB in `test_endpoints.py`

## Phase 2: Engine+Schemas (PR#2) — P1, ~450 LOC

- [ ] 2.1 Create `ai_insights/__init__.py` exporting `router`
- [ ] 2.2 Create `schemas.py`: `SupportingMetric`, `Insight`, `InsightContext`, `SummaryResponse`, `DetailResponse`
- [ ] 2.3 Create `rules/__init__.py` with `RULE_REGISTRY`
- [ ] 2.4 Create 6 rules: `win_rate_trend`, `profit_factor_health`, `drawdown_risk`, `edge_significance`, `edge_insufficient`, `concentration_risk`
- [ ] 2.5 Create `dependencies.py` with `get_ai_insights_service`
- [ ] 2.6 Create `service.py`: `AIInsightsService` — `collect_context`, `get_summary`, `get_detail`, `refresh`
- [ ] 2.7 Snapshot tests: known context → assert insight fields + byte-identical 3 runs
- [ ] 2.8 Determinism: same input → byte-identical output
- [ ] 2.9 Partial failure: one service empty → graceful degradation

## Phase 3: API Layer (PR#3) — P2, ~350 LOC

- [ ] 3.1 Create `router.py`: `GET /summary`, `GET /detail/{id}`, `POST /refresh`
- [ ] 3.2 Validation: refresh→202, invalid ID→404, summary has `by_severity`
- [ ] 3.3 Integration: httpx seeded trades, all 3 endpoints 200+shape
- [ ] 3.4 Empty: no trades → `total_count:0, insights:[], confidence:low`
- [ ] 3.5 OpenAPI: `/openapi.json` includes 3 new paths

## Phase 4: Frontend (PR#4) — P2, ~500 LOC

- [ ] 4.1 Create `services/aiInsightsApi.js`: `getSummary`, `getDetail`, `refresh`
- [ ] 4.2 Create hooks: `useInsights`, `useInsightDetail`, `useRefreshInsights`
- [ ] 4.3 Create `InsightCard.jsx`: severity badge, message, confidence, rec
- [ ] 4.4 Create `InsightDetail.jsx`: drill-down per insight
- [ ] 4.5 Create `EvidenceChain.jsx`: supporting_metrics[] + trade_ids[]
- [ ] 4.6 Create `AIInsightsDashboard.jsx`: grouped by severity, skeleton(3), empty, ErrorFallback+retry
- [ ] 4.7 Create `pages/AIInsightsDashboard.jsx`: wrapper + refresh button
- [ ] 4.8 Modify `App.jsx`: lazy route `/analytics/insights`
- [ ] 4.9 Hook tests (3 files): mock API, assert loading/success/error
- [ ] 4.10 Component tests (4 files): fixture data assert skeleton/empty/success/error

## Dep Graph

```
PR#1 standalone → PR#2 (needs analytics data) → PR#3 (needs service) → PR#4 (needs endpoints)
```
