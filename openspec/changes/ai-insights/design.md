# Design: AI Insights (v1.5.0)

## Technical Approach

Two domains delivered as independent PRs. (1) **risk-analytics wiring**: add 5 routes, 5 service methods, and 3 response schemas to the existing `analytics` module — calculators already exist, no new metrics. (2) **ai-insights module**: new self-contained FastAPI module under `backend/app/modules/ai_insights/` with a deterministic rule engine (pure Python, no AI deps). Zero changes to existing contracts.

## Architecture Decisions

### Decision: Module auto-discovery for ai-insights

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Manual router registration in main.py | Explicit but requires changing `main.py` | Rejected — breaks C6 |
| Auto-discovery via `discover_modules()` | Zero-config — just add `router.py` | **Chosen** — follows existing convention in `modules/__init__.py` |

All existing modules register automatically. Adding `app/modules/ai_insights/router.py` with `router = APIRouter(prefix="/api/ai-insights", ...)` requires zero changes elsewhere.

### Decision: DataCollector couples to services, not calculators

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Call calculators directly | Faster, but bypasses service layer | Rejected — violates ADR-008 traceability |
| Call AnalyticsService + EdgeDiscoveryService | Traceable, handles partial failure | **Chosen** — DI injects both services |

DataCollector calls `AnalyticsService.get_summary()` and `EdgeDiscoveryService.get_rankings()` (DI-injected). A module being down produces degraded insights, never a crash.

### Decision: Rule registry via module-level dict, not config files

| Option | Tradeoff | Decision |
|--------|----------|----------|
| YAML config for rules | Flexible, but adds parsing + validation | Rejected — over-engineering for <12 rules |
| Plugin discovery | Autoloads new rule files | Rejected — implicit |
| Module-level `registry` dict in `rules/__init__.py` | Explicit, testable, self-documenting | **Chosen** — each rule module appends to `RULE_REGISTRY` on import |

### Decision: Insight schema uses `severity` + `confidence` (not `confidence` float)

Spec defines `confidence: 0.0–1.0` but the orchestrator's prompt specifies `severity: info|warning|critical` with a separate `confidence: high|medium|low`. **Chosen**: follow the explicit schema from the launch prompt — aligns with how existing modules surface severity (e.g., drawdown > 20% is `critical`, win-rate dip is `warning`).

## Data Flow

```
Client → GET /api/ai-insights/summary?account_id=...

  AIInsightsService.collect_context(filters)
    ├─ AnalyticsService.get_summary(filters)     → PerformanceMetrics, RiskMetrics
    ├─ AnalyticsService.get_breakdown_asset(filters) → asset exposure
    └─ EdgeDiscoveryService.get_rankings()        → EdgeScore[]

  RuleEngine.evaluate(context)                    → List[Insight]
    ├─ win_rate_trend(context)   → Insight | None
    ├─ profit_factor_health(context) → Insight | None
    ├─ drawdown_risk(context)    → Insight | None
    ├─ edge_significance(context) → Insight | None
    ├─ edge_insufficient(context) → Insight | None
    └─ concentration_risk(context) → Insight | None

  ResponseAssembly(insights)                      → SummaryResponse
    └─ Group by severity, assign IDs

Client ← 200 { insights: [...], by_severity: {...} }
```

Partial failure: `AnalyticsService` returns empty dict → `concentration_risk` returns None, other rules still evaluate. `EdgeDiscoveryService` returns empty → edge rules produce None.

## File Changes

### Domain 1: ai-insights (new module)

| File | Action | Description |
|------|--------|-------------|
| `backend/app/modules/ai_insights/__init__.py` | Create | Export `router` for auto-discovery |
| `backend/app/modules/ai_insights/schemas.py` | Create | Insight, SupportingMetric, InsightContext, SummaryResponse, DetailResponse |
| `backend/app/modules/ai_insights/service.py` | Create | AIInsightsService — collect_context(), get_summary(), get_detail(), refresh() |
| `backend/app/modules/ai_insights/router.py` | Create | 3 endpoints: GET summary, GET detail/{id}, POST refresh |
| `backend/app/modules/ai_insights/dependencies.py` | Create | DI provider for AIInsightsService |
| `backend/app/modules/ai_insights/rules/__init__.py` | Create | RULE_REGISTRY dict, rule discovery |
| `backend/app/modules/ai_insights/rules/win_rate_trend.py` | Create | Rule: win rate < 40% → insight |
| `backend/app/modules/ai_insights/rules/profit_factor_health.py` | Create | Rule: PF < 1.0 → insight |
| `backend/app/modules/ai_insights/rules/drawdown_risk.py` | Create | Rule: drawdown > 20% → insight |
| `backend/app/modules/ai_insights/rules/edge_significance.py` | Create | Rule: p<0.05 & stability>0.7 → insight |
| `backend/app/modules/ai_insights/rules/edge_insufficient.py` | Create | Rule: filtered by statistical gate → insight |
| `backend/app/modules/ai_insights/rules/concentration_risk.py` | Create | Rule: single asset/strategy > 40% exposure |
| `frontend/src/modules/ai-insights/pages/AIInsightsDashboard.jsx` | Create | Main insights page |
| `frontend/src/modules/ai-insights/components/InsightCard.jsx` | Create | Individual insight card |
| `frontend/src/modules/ai-insights/components/InsightDetail.jsx` | Create | Drill-down detail with evidence chain |
| `frontend/src/modules/ai-insights/components/EvidenceChain.jsx` | Create | Supporting metrics + trades display |
| `frontend/src/modules/ai-insights/hooks/useInsights.js` | Create | useQuery wrapper for summary |
| `frontend/src/modules/ai-insights/hooks/useInsightDetail.js` | Create | useQuery wrapper for detail |
| `frontend/src/modules/ai-insights/hooks/useRefreshInsights.js` | Create | useMutation for refresh |
| `frontend/src/modules/ai-insights/services/aiInsightsApi.js` | Create | API bridge for 3 endpoints |
| `frontend/src/App.jsx` | Modify | Add route for `/analytics/insights` (lazy import) |
| `backend/tests/modules/ai_insights/test_rules.py` | Create | Rule unit tests — snapshot-based |
| `backend/tests/modules/ai_insights/test_service.py` | Create | Service tests with mocked dependencies |
| `backend/tests/modules/ai_insights/test_endpoints.py` | Create | Integration tests via httpx |

### Domain 2: risk-analytics wiring

| File | Action | Description |
|------|--------|-------------|
| `backend/app/modules/analytics/schemas.py` | Modify | Add RiskMetricsResponse, ExposureResponse, ExposureItem, CorrelationResponse, CorrelationItem |
| `backend/app/modules/analytics/service.py` | Modify | Add get_risk_metrics(), get_exposure_by_asset(), get_exposure_by_session(), get_exposure_by_strategy(), get_correlation() |
| `backend/app/modules/analytics/router.py` | Modify | Add 5 routes matching frontend expectations |
| `backend/app/modules/analytics/calculators/risk.py` | Modify | Add private _compute_holding_time(), _compute_kelly(), _compute_ror() helpers |
| `backend/tests/modules/analytics/test_endpoints.py` | Modify | Add integration tests for 5 new endpoints |
| `backend/tests/modules/analytics/test_service.py` | Modify | Add service method tests |

### Route paths (mapping frontend hooks to backend)

| Frontend Hook | API Path | Backend Method |
|--------------|----------|---------------|
| `useRiskMetrics(capital)` | `GET /api/analytics/risk-metrics?capital=X` | `get_risk_metrics(filters, capital)` |
| `useExposureByAsset()` | `GET /api/analytics/exposure/by-asset` | `get_exposure_by_asset(filters)` |
| `useExposureBySession()` | `GET /api/analytics/exposure/by-session` | `get_exposure_by_session(filters)` |
| `useExposureByStrategy()` | `GET /api/analytics/exposure/by-strategy` | `get_exposure_by_strategy(filters)` |
| `useCorrelation(minTrades)` | `GET /api/analytics/exposure/correlation?min_trades=X` | `get_correlation(filters, min_trades)` |

## Interfaces / Contracts

### Domain 1: Insight schemas

```python
class SupportingMetric(BaseModel):
    name: str
    value: float
    source: Literal["analytics", "risk", "edge"]
    endpoint: str

class Insight(BaseModel):
    id: str
    category: str
    severity: Literal["info", "warning", "critical"]
    title: str
    message: str
    supporting_metrics: list[SupportingMetric]
    trade_ids: list[int]
    confidence: Literal["high", "medium", "low"]
    recommendation: str | None

class InsightContext(BaseModel):
    summary: SummaryResponse | None = None
    asset_breakdown: AssetBreakdownResponse | None = None
    edge_rankings: EdgeRankingResponse | None = None

class SummaryResponse(BaseModel):
    insights: list[Insight]
    total_count: int
    by_severity: dict[str, int]

class DetailResponse(BaseModel):
    insight: Insight
    context: InsightContext
```

### Domain 2: Risk-analytics schemas (added to schemas.py)

```python
class RiskMetricsResponse(BaseModel):
    max_drawdown: float
    max_drawdown_pct: float
    current_drawdown: float
    current_drawdown_pct: float
    recovery_factor: float | None = None
    payoff_ratio: float | None = None
    holding_time: HoldingTime | None = None
    kelly_percentage: float | None = None
    ror_ratio: float | None = None

class ExposureItem(BaseModel):
    id: int
    name: str | None
    notional: float | None = None
    trade_count: int
    total_pnl: float | None = None
    total_risk_amount: float | None = None

class ExposureResponse(BaseModel):
    items: list[ExposureItem]

class CorrelationItem(BaseModel):
    asset_a_id: int
    asset_a_name: str | None
    asset_b_id: int
    asset_b_name: str | None
    correlation: float | None
    trade_count: int

class CorrelationResponse(BaseModel):
    pairs: list[CorrelationItem]
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit — rules | Each rule: known context → expected insight or None | Snapshot-based: fixed InsightContext input → assert fields match |
| Unit — helpers (risk.py) | `_compute_holding_time`, `_compute_kelly`, `_compute_ror` | Known trade lists → expected float values |
| Service — risk-analytics | get_risk_metrics, get_exposure_*, get_correlation | Mock `list_closed` → assert response shape |
| Integration — endpoints | 5 new risk-analytics + 3 ai-insights endpoints | httpx client, seeded trades, assert 200 + schema |
| Integration — frontend | useInsights, useInsightDetail, useRefreshInsights | Mock API, assert loading/success/error states |
| Component — frontend | InsightCard, InsightDetail, EvidenceChain | Render fixture data, assert all 4 states per pattern |
| Determinism | RuleEngine.evaluate() | Same context → byte-identical output × 3 runs |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary.

## Migration / Rollout

No migration required. Both domains are additive:
- risk-analytics wiring: new routes behind existing prefix, existing routes unchanged
- ai-insights: new module directory, auto-discovered by `discover_modules()`
- Frontend: new route `/analytics/insights` added (lazy-loaded), no existing route affected

Rollback: revert the commit. Every file is additive or strictly additive within existing files. No contract changes.

## Open Questions

None. All decisions resolved against existing codebase patterns.
