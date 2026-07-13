# Exploration: v1.5.0 AI Insights Module

> **Project**: DashboardTrading — Trade Intelligence Platform (TIP)
> **Objective**: Construir el módulo **AI Insights** como consumidor del motor analítico existente. La IA **no** calculará métricas ni descubrirá edges; únicamente **interpretará resultados** provenientes de Analytics, Risk Analytics y Edge Discovery.

---

## 1. Existing Analytics Modules

### 1.1 Core Analytics (`backend/app/modules/analytics/`)

**Location**: `backend/app/modules/analytics/`

**Structure**:
```
analytics/
├── __init__.py              # Exports router
├── router.py                # 16+ read-only endpoints
├── service.py               # AnalyticsService orchestrator
├── schemas.py               # All Pydantic models (236 lines)
├── dependencies.py          # DI: get_analytics_service
└── calculators/
    ├── __init__.py          # Calculator registry
    ├── pnl.py               # compute_pnl(trade) → float
    ├── performance.py       # compute_performance(trades) → dict
    ├── risk.py              # compute_risk(trades) → dict (drawdown, payoff)
    ├── exposure.py          # exposure by asset/session/strategy
    ├── correlation.py       # Pearson cross-asset correlation
    ├── breakdown.py         # by_asset / by_direction / by_market
    ├── context_breakdown.py # by_strategy / by_setup / by_tag / by_mistake
    ├── distribution.py      # R-multiple distribution
    ├── heatmap.py           # Day/hour heatmap
    ├── rolling.py           # Sliding window metrics
    └── timeseries.py        # Equity curve, streaks, PnL by period
```

**Key Pattern**: All calculators are **pure functions**: `list[Trade] → dict`. They receive a list of ORM `Trade` objects and return plain dicts that get validated into Pydantic models.

**Service Pattern** (309 lines):
- Constructor takes `UnitOfWork` only
- Each method: `list_closed()` → calculator → Pydantic response
- Single `list_closed()` call per method (N+1 avoided by design)

**Available Endpoints** (all `GET /api/analytics/...`):

| Endpoint | Response Model | Key Fields |
|----------|---------------|------------|
| `/summary` | `SummaryResponse` | `total_trades`, `performance` (net_pnl, win_rate, profit_factor, expectancy, avg_r_multiple), `risk` (max_drawdown, recovery_factor, payoff_ratio) |
| `/equity` | `EquityResponse` | `equity_curve[]`, `streaks`, `pnl_daily/weekly/monthly` |
| `/performance` | `PerformanceResponse` | Same as summary's performance block |
| `/breakdown/asset` | `AssetBreakdownResponse` | Per-asset: trade_count, net_pnl, win_rate, profit_factor, expectancy |
| `/breakdown/direction` | `DirectionBreakdownResponse` | Long vs Short as `PerformanceMetrics` |
| `/breakdown/market` | `MarketBreakdownResponse` | Per-market metrics |
| `/breakdown/strategies` | `BreakdownResponse` | `BreakdownItem[]` (id, name, trade_count, win_rate, net_pnl, expectancy) |
| `/breakdown/setups` | `BreakdownResponse` | Same structure |
| `/breakdown/tags` | `BreakdownResponse` | Same structure |
| `/breakdown/mistakes` | `BreakdownResponse` | Same structure |
| `/distribution/r` | `RDistributionResponse` | Bucketed R-multiple histogram |
| `/heatmap` | `HeatmapResponse` | Day/hour trade_count + net_pnl |
| `/rolling` | `RollingResponse` | Sliding window: win_rate, profit_factor, expectancy, avg_r_multiple |
| `/performance/by-period` | `PerformanceByPeriodResponse` | Grouped by month/quarter/year |
| `/performance/compare` | `ComparePeriodsResponse` | Two periods with delta and delta_percent |

### 1.2 Risk Analytics (`backend/app/modules/analytics/calculators/`)

**⚠️ IMPORTANT**: The risk-analytics backend endpoints are **DESIGNED BUT NOT YET IMPLEMENTED**. The `openspec/changes/risk-analytics/design.md` specifies 5 new endpoints, but:
- The analytics `router.py` has no `/risk-metrics`, `/exposure/*`, or `/correlation` routes
- The analytics `service.py` has no `get_risk_metrics()`, `get_exposure_*()`, or `get_correlation()` methods
- The analytics `schemas.py` has no `RiskMetricsResponse`, `ExposureResponse`, or `CorrelationResponse`

**However**, the calculators already exist:
- `calculators/risk.py` — only has `compute_risk()` (drawdown metrics). The extended risk metrics (holding time, kelly, RoR) from the design doc are NOT yet implemented
- `calculators/exposure.py` — `compute_exposure_by_asset()`, `compute_exposure_by_session()`, `compute_exposure_by_strategy()` — **EXIST**
- `calculators/correlation.py` — `compute_correlation()` — **EXISTS**

**Frontend status**: Hooks and components exist in `frontend/src/modules/risk-management/`, but they call non-existent backend endpoints. They will fail if called.

### 1.3 Edge Discovery (`backend/app/modules/edge_discovery/`)

**Location**: `backend/app/modules/edge_discovery/`

**Structure**:
```
edge_discovery/
├── __init__.py                    # Public API exports
├── router.py                      # 7 endpoints
├── service.py                     # EdgeDiscoveryService
├── schemas.py                     # Pydantic models (API I/O)
├── models.py                      # Domain dataclasses (engine internals)
├── dependencies.py                # DI chain
├── db.py                          # aiosqlite connection
├── engine/
│   ├── edge_discovery_engine.py   # Orchestrator pipeline
│   ├── combinator.py              # Dimension group enumeration
│   ├── scorer.py                  # Edge score computation
│   ├── stability.py               # Split-half stability
│   ├── fdr.py                     # Benjamini-Hochberg correction
│   └── statistical_gate.py        # Confidence level gating
├── implementations/
│   ├── sqlite_edge_repository.py  # JSON blob storage
│   └── numpy_statistics_engine.py # Bootstrap CI + p-values
└── interface/
    ├── edge_repository.py         # Abstract repository
    └── statistics_engine.py       # Abstract statistics
```

**Key Output Models**:

`EdgeScore` (returned for each group):
```python
group_id: str
dimensions: dict[str, str | None]         # e.g. {"strategy": "breakout", "direction": "long"}
trade_ids: list[int]
trade_count: int
expectancy: float
net_pnl: float
profit_factor: float | None
confidence_interval: tuple[float, float]   # 95% CI from bootstrap
p_value: float
fdr_adjusted_p_value: float
stability_score: float                     # split-half
edge_score: float                          # composite
confidence_level: Literal["high", "medium", "low", "insufficient"]
failure_reasons: list[str]
```

`TradeInput` (engine input):
```python
id: int
strategy: str | None
setup: str | None
session: str | None
asset: str | None
direction: str | None
exit_datetime: str | None
pnl: float
risk_amount: float | None
```

**Available Endpoints**:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/edges/generate` | POST | Background generation (requires admin key) |
| `/api/analytics/edges/` | GET | Latest rankings (optional `show_insufficient`) |
| `/api/analytics/edges/tags` | GET | Tag impact (stub — returns `[]`) |
| `/api/analytics/edges/mistakes` | GET | Mistake impact (stub — returns `[]`) |
| `/api/analytics/edges/snapshots` | GET | List all snapshots |
| `/api/analytics/edges/snapshots/{id}` | GET | Specific snapshot rankings |
| `/api/analytics/edges/{group_id}` | GET | Single edge detail |

---

## 2. Data Contracts & Schemas — Complete Pydantic Model Inventory

### Analytics Schemas (`schemas.py`)
| Model | Purpose | Key Fields for AI |
|-------|---------|-------------------|
| `AnalyticsFilter` | Shared query filter | `account_id`, `asset_id`, `market_id`, `date_from`, `date_to`, `window_size` |
| `PerformanceMetrics` | Core performance | `net_pnl`, `win_rate`, `profit_factor`, `expectancy`, `avg_r_multiple` |
| `RiskMetrics` | Drawdown | `max_drawdown_pct`, `recovery_factor`, `payoff_ratio` |
| `SummaryResponse` | Combined summary | `total_trades`, `total_open_trades`, `performance`, `risk` |
| `EquityResponse` | Time series | `equity_curve[]`, `streaks`, `pnl_daily/weekly/monthly` |
| `AssetBreakdown` | Per-asset | `symbol`, `trade_count`, `net_pnl`, `win_rate`, `profit_factor`, `expectancy` |
| `BreakdownItem` | Common breakdown | `id`, `name`, `trade_count`, `win_rate`, `net_pnl`, `expectancy`, `avg_win`, `avg_loss` |
| `DirectionBreakdownResponse` | Direction | `long`, `short` as `PerformanceMetrics` |
| `RDistributionItem` | R-multiple bucket | `bucket` (label), `count` |
| `HeatmapItem` | Time heatmap | `day` (0-6), `hour` (0-23), `trade_count`, `net_pnl` |
| `RollingPoint` | Rolling window | `index`, `win_rate`, `profit_factor`, `expectancy`, `avg_r_multiple`, `trade_count` |
| `PerformanceByPeriodRecord` | Period metrics | `period`, `trade_count`, `net_pnl`, `win_rate`, `profit_factor`, `expectancy` |
| `ComparePeriodsResponse` | Comparison | `period_a`, `period_b`, `delta`, `delta_percent` |

### Edge Discovery Schemas (`schemas.py`)
| Model | Key Fields for AI |
|-------|-------------------|
| `EdgeScore` | `dimensions`, `expectancy`, `net_pnl`, `p_value`, `fdr_adjusted_p_value`, `stability_score`, `edge_score`, `confidence_level`, `failure_reasons`, `confidence_interval` |
| `EdgeRankingResponse` | `snapshot_id`, `rankings[]` |
| `EdgeDetailResponse` | `edge` (single EdgeScore) |
| `TagImpact` | `tag_name`, `trade_count`, `expectancy`, `net_pnl` |
| `MistakeImpact` | `mistake_name`, `trade_count`, `expectancy`, `net_pnl` |

### What AI Would Need to Interpret

The AI Insights module would consume these data points from the existing modules:

**From Analytics**:
- **Performance trends**: Period-over-period changes in win_rate, profit_factor, expectancy, avg_r_multiple
- **Breakdown patterns**: Which strategies/setups/tags/mistakes correlate with positive/negative performance
- **Risk evolution**: Drawdown trends, recovery factor history
- **Distribution shape**: R-multiple clustering, trade outcome distribution
- **Rolling metrics**: Degradation or improvement over recent trades
- **Heatmap**: Time-based performance patterns

**From Edge Discovery**:
- **Ranked edges**: Which dimension combinations show statistically significant edges
- **Statistical rigor**: p-values, FDR adjustment, stability scores, confidence intervals
- **Confidence levels**: Which edges pass the statistical gate vs. which are insufficient
- **Failure reasons**: Why specific groups failed the statistical gate

**From Risk Analytics** (when implemented):
- Kelly fraction, risk of ruin, exposure concentration, cross-asset correlation

---

## 3. Frontend Modules

### Analytics Frontend (`frontend/src/modules/analytics/`)

**Structure**:
```
modules/analytics/
├── pages/
│   └── DashboardPage.jsx        # Main dashboard — 13 simultaneous React Query hooks
├── components/
│   ├── FiltersBar.jsx
│   ├── SummaryCards.jsx
│   ├── EquityChart.jsx
│   ├── AssetBreakdownTable.jsx
│   ├── DirectionBreakdown.jsx
│   ├── BreakdownTable.jsx       # Reusable for strategies/setups/tags/mistakes
│   ├── RHistogram.jsx
│   ├── HeatmapChart.jsx
│   ├── RollingMetricsChart.jsx
│   ├── PerformanceByPeriod.jsx
│   └── PeriodComparison.jsx
├── hooks/
│   ├── useDashboardFilters.js   # URL-synced filter state
│   ├── useSummary.js
│   ├── useEquity.js
│   ├── useAssetBreakdown.js
│   ├── useDirectionBreakdown.js
│   ├── useBreakdownStrategies.js
│   ├── useBreakdownSetups.js
│   ├── useBreakdownTags.js
│   ├── useBreakdownMistakes.js
│   ├── useRDistribution.js
│   ├── useHeatmap.js
│   ├── useRollingMetrics.js
│   ├── usePerformanceByPeriod.js
│   └── usePerformanceComparison.js
├── services/
│   └── analyticsApi.js          # API bridge — 14 methods
└── utils/
    ├── constants.js             # QUERY_KEYS factory, chart colors
    └── formatters.js            # formatCurrency, formatPercent, etc.
```

**Key Pattern**: Each hook is a `useQuery` wrapper. `useDashboardFilters()` reads/writes URL search params and is the single source of truth. Filters propagate through `queryKey` dependencies for auto-refetch.

### Risk Management Frontend (`frontend/src/modules/risk-management/`)

**Structure**:
```
modules/risk-management/
├── components/
│   ├── RiskDashboard.jsx        # Composite — 5 hooks, 3 sub-components
│   ├── RiskMetricsCards.jsx     # 8 metric cards
│   ├── ExposureTable.jsx        # Tabs: by-asset, by-session, by-strategy
│   └── CorrelationMatrix.jsx    # Pearson R table
├── hooks/
│   ├── useRiskMetrics.js
│   ├── useExposureByAsset.js
│   ├── useExposureBySession.js
│   ├── useExposureByStrategy.js
│   └── useCorrelation.js
└── services/
    └── riskAnalyticsApi.js      # API bridge — 5 methods (calls /analytics/* endpoints)
```

**⚠️** Backend endpoints for these hooks are NOT yet implemented.

### Edge Discovery Frontend (`frontend/src/modules/edge-discovery/`)

**Structure**:
```
modules/edge-discovery/
├── pages/
│   ├── EdgeDiscoveryPage.jsx    # Rankings table + generate button
│   └── EdgeDetailPage.jsx       # Single edge drilldown
├── components/
│   ├── EdgeRankingTable.jsx     # Sortable table, links to detail
│   ├── EdgeScoreCard.jsx        # Visual metrics card
│   ├── EdgeDetailDrilldown.jsx  # Trade list for an edge
│   └── EdgeStabilityIndicator.jsx
├── hooks/
│   ├── useEdgeRankings.js       # useQuery + useMutation (generate)
│   └── useEdgeDetail.js         # useQuery for single edge
└── services/
    └── edge-discovery.service.js # 7 API methods
```

**Pattern**: Edge hooks use `staleTime: Infinity` (point-in-time snapshots, no auto-refetch).

### Shared Patterns

All frontend modules follow a consistent contract for component props:
```javascript
{
  data,              // API response (or undefined)
  isLoading,         // React Query isFetching
  isError,           // Error state
  error,             // Error object
  onRetry,           // refetch callback
}
```

All components handle 4 states: **loading** (Skeleton), **error** (ErrorFallback), **empty** (explicit UI), **success** (data render).

---

## 4. Existing Module Patterns

### Backend Module Registration (Auto-Discovery)

```python
# backend/app/modules/__init__.py
def discover_modules() -> list[APIRouter]:
    """Scan modules/ directory, import each subpackage's router.py"""
```

**Contract**: Create a new folder under `app/modules/<name>/` with:
- `__init__.py` — exports `router`
- `router.py` — defines `router = APIRouter(...)`
- `schemas.py` — Pydantic models
- `service.py` — business logic class
- `dependencies.py` — FastAPI `Depends` providers

**Zero configuration** — the module is auto-discovered at startup.

### Dependency Injection Chain

```
get_db (session) → get_uow (UnitOfWork) → get_<module>_service → router endpoint
```

Services receive either `UnitOfWork` directly (simple services) or composed dependencies (edge discovery has engine + repository + UoW).

### Testing Patterns

**Calculator tests**: Pure function assertions — known input → expected output.
```python
def test_empty_trades():
    assert compute_performance([]) == {...}
```

**Service tests**: Mock `uow.trades.list_closed`, verify response shape + single call.
```python
svc.uow.trades.list_closed = AsyncMock(return_value=[mock_trade])
result = await svc.get_summary(AnalyticsFilter())
assert isinstance(result, SummaryResponse)
svc.uow.trades.list_closed.assert_awaited_once()
```

**Endpoint tests**: httpx `AsyncClient`, seed DB via trade API, assert status + response body.

**Test infrastructure** (`conftest.py`):
- Session-scoped in-memory SQLite engine
- Per-test transaction-scoped session (rollback after each test)
- Per-test FastAPI `AsyncClient` with overridden `get_db` dependency
- See actual fixtures in `backend/tests/conftest.py`

**Edge Discovery tests** (6 test files): Pure function tests for combinator, scorer, FDR, stability, statistical gate, numpy engine, SQLite repository.

---

## 5. LLM Integration Possibilities

### Current State
- **No existing AI/LLM integration** — zero references to openai, anthropic, langchain, or any AI library
- **No LLM dependencies** in `pyproject.toml` (dependencies: fastapi, uvicorn, sqlalchemy, aiosqlite, alembic, pydantic-settings, numpy)
- **No prompt templates, no AI configuration, no API key management**

### Architecture Approaches

| Approach | Pros | Cons | Recommendation |
|----------|------|------|---------------|
| **Server-side LLM calls** (Python → OpenAI API) | Centralized key mgmt, better error handling | Breaks offline-first, adds latency, introduces API dependency | ⚠️ Conflicts with ADR-003 |
| **Client-side LLM calls** (JS → OpenAI API) | Keeps backend pure, no infra changes | Exposes API keys, duplicates logic, breaks offline | ⛔ Not recommended |
| **Local LLM (server-side embedding/run)** | Preserves offline-first | Requires `llama-cpp-python` or similar, heavy dependency, limited capability | Potentially viable but heavyweight |
| **Template-based rule engine** (no LLM) | Fully offline, deterministic, testable | Limited "insight" quality, no natural language | ✅ Best fit for MVP |
| **Hybrid: local rules + optional cloud LLM** | Offline core, enhanced when online | Two code paths, testing complexity | Most pragmatic v1 |

### Key Constraint: Offline-First Architecture

ADR-003 mandates SQLite as the production database. The platform must work fully offline. This fundamentally conflicts with external AI APIs.

**Recommendation for v1**: Build a **structured insight engine** using a template/reasoning system (not an LLM) that:
1. Receives the analytics data structures
2. Applies rule-based reasoning (e.g., "if win_rate < 0.4 and expectancy < 0, then pattern is negative")
3. Outputs structured JSON with: `observation`, `supporting_metrics[]`, `confidence_level`, `recommendation`
4. Preserves full traceability to individual metrics and trades (ADR-008)

An LLM integration could be added later at the **frontend layer** for generating natural-language summaries of the structured insights, as an optional enhancement when online.

### Python Libraries Available

Current available: `numpy` only. For LLM integration would need:
- `openai` — for OpenAI API
- `anthropic` — for Claude API
- `llama-cpp-python` — for local LLM (CPU, heavy)
- `httpx` — for any custom API calls (already a test dependency)

### Prompt Template Architecture (If LLM Chosen)

```python
class InsightRequest(BaseModel):
    summary: SummaryResponse
    breakdowns: dict[str, list[BreakdownItem]]
    edges: EdgeRankingResponse | None = None
    period_comparison: ComparePeriodsResponse | None = None
    rolling_metrics: RollingResponse | None = None

class InsightResponse(BaseModel):
    observations: list[InsightObservation]
    requires_attention: list[str]
    confidence: Literal["high", "medium", "low"]

class InsightObservation(BaseModel):
    metric: str                  # e.g. "expectancy"
    current_value: float
    previous_value: float | None
    direction: Literal["improving", "declining", "stable"]
    significance: float          # statistical significance or magnitude
    supporting_trades: list[int] # ADR-008 traceability
    narrative: str               # AI-generated explanation
```

---

## 6. Risk & Constraints

### ADR-008 — Chain of Evidence
The requirement that every conclusion must be traceable to metrics and individual trades has deep implications for the AI Insights architecture:

- **Every insight must cite its source**: metric name, current value, and trade IDs or dimension groups
- **Structured output is required** (not free-text) to enforce traceability
- **Insufficient evidence must be explicitly stated** — the AI must return a "low confidence" path when data is insufficient
- **Testing requirement**: Tests must verify that every observation includes valid `supporting_trades[]` and `supporting_metrics[]` references
- **Schema design**: The `InsightObservation` model must enforce these fields as non-optional

### Testing Requirements for AI Outputs

| Concern | Approach |
|---------|----------|
| **Determinism** | Rule-based engine must produce identical output for identical input |
| **Grounding** | Every insight references real metric values and trade IDs |
| **Insufficient data** | Empty trade list → "no data" response, not a hallucination |
| **Monte Carlo sensitivity** | If using statistical methods, seed for reproducibility |
| **Edge cases** | Single trade, all losses, no risk_amount, empty breakdowns |
| **Regression tests** | Snapshot-based: known input → expected insight output |

### Performance Considerations

- If using an external LLM API: every request adds 500ms-5s latency. Cache LLM results keyed by `hash(all_input_data)`
- If using local LLM: CPU-only inference is slow (5-30s). Consider quantized models (GGUF)
- Rule-based engine: essentially instant (< 50ms)
- **Recomputation triggers**: On-demand (user clicks "Generate Insights") NOT on every dashboard load
- Edge discovery already uses background tasks — AI Insights should follow the same pattern for heavy computation

### Offline-First vs External AI APIs

| Scenario | Works? | Notes |
|----------|--------|-------|
| Rule-based engine (server) | ✅ | Fully offline, no external deps |
| Local LLM (llama.cpp) | ✅ | Heavy dependency but works offline |
| OpenAI API (server-side) | ❌ | Requires internet |
| OpenAI API (client-side) | ❌ | Requires internet + exposes keys |
| Cloud AI gateway | ❌ | Requires internet |

**Recommendation**: The AI Insights v1 MUST work fully offline. Use a structured rule/reasoning engine. LLM enrichment is a v2 enhancement that could be added as an optional layer.

### Data Volume Considerations

- Analytics methods already load all filtered trades into memory (`list_closed()` is unfiltered by trade count, only by date/account/asset)
- Edge discovery engine does in-memory bootstrap (10k resamples by default) — already handles CPU-intensive work
- AI Insights would consume the **outputs** of these modules (the Pydantic models), NOT the raw trades
- Maximum AI input: ~15 API response payloads (all analytics endpoints + edges) — well within memory limits

### Module Isolation

- AI Insights MUST be a separate module (`backend/app/modules/ai_insights/`)
- It MUST NOT import from calculators directly — only consume data through existing API responses or the service layer
- The module gets data by calling existing AnalyticsService and EdgeDiscoveryService methods (not duplicating queries)
- Frontend gets its own page + hooks + components, following the existing pattern

---

## Key Findings Summary

| Finding | Impact |
|---------|--------|
| No LLM deps exist | Must add dependencies IF choosing LLM path |
| Risk-analytics backends not implemented | AI cannot consume these endpoints yet — either wait or implement them as part of this change |
| Rule engine > LLM for v1 | Preserves ADR-003 (offline-first), deterministic, testable |
| Module auto-discovery | Zero-config registration for new module |
| Calculator pattern | Pure functions are easy to test and compose |
| Edge Discovery snapshot model | AI could reference snapshot IDs as evidence sources |
| Frontend ErrorBoundary pattern | New AI Insights components follow the same contract |
| ADR-008 chain of evidence | Drives schema design — every insight MUST cite metrics+trades |
| Background tasks pattern | Already established by edge discovery generation |

---

## Recommended Architecture for Proposal Phase

```
Layer 1 — Data Collection: AIInsightsService calls existing services/methods
    → AnalyticsService.get_summary(), .get_breakdown_*(), .get_rolling_metrics(), etc.
    → EdgeDiscoveryService.get_rankings()
    
Layer 2 — Rule Engine: Pure functions that analyze collected data
    → detect_performance_trends(summary, comparison)
    → detect_breakdown_anomalies(breakdowns[])
    → evaluate_edge_quality(edges[])
    → synthesize_insights(all_observations)
    
Layer 3 — Output: Structured InsightResponse
    → observations[] with supporting_metrics + supporting_trades
    → confidence_level per observation
    → explicit "insufficient data" when appropriate

Layer 4 — Frontend: New module page
    → /analytics/insights route
    → InsightList component with observations grouped by category
    → Each observation linked to source metric/trade
```

---

*Exploration completed: 2026-07-11*
*Next phase: Proposal*
