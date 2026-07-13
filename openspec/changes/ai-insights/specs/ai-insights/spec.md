# AI Insights Specification

## Purpose

Deterministic rule engine that consumes validated evidence from Analytics, Risk Analytics, and Edge Discovery — never invents data, never calculates metrics. Every insight cites its supporting metrics and trades. When evidence is insufficient, the engine explicitly says so.

## Requirements

### Requirement: Insight Schemas

The system MUST define Pydantic models for structured insights.

| Field | Type | Rule |
|-------|------|------|
| `category` | str | One of: `performance`, `risk`, `edge`, `composite` |
| `severity` | str | One of: `info`, `warning`, `critical` |
| `message` | str | Human-readable insight statement |
| `supporting_metrics` | list[MetricRef] | At least 1 entry — `{name, value, source}` |
| `supporting_trades` | list[int] | Trade IDs or empty list with explicit note |
| `confidence` | float | 0.0–1.0 |
| `recommendation` | str | Actionable guidance or `"none"` |

#### Scenario: Full insight with evidence chain

- GIVEN validated Analytics metrics + Edge scores
- WHEN engine produces an insight
- THEN `supporting_metrics` MUST contain ≥1 reference AND `supporting_trades` MUST list trade IDs OR message includes "no specific trades"

#### Scenario: Insufficient evidence

- GIVEN all source data is empty or below minimum thresholds
- THEN every field indicates insufficiency — `message` contains "insufficient evidence", `supporting_metrics` empty

#### Scenario: Conflicting signals

- GIVEN two rules produce contradictory conclusions for the same category
- THEN the engine surfaces both with `severity: "warning"` and `message` notes the conflict explicitly

### Requirement: Rule Engine

The system MUST provide a deterministic, pure-Python rule engine. Each rule is a standalone function: `(context: InsightContext) → Insight | None`.

| Property | Constraint |
|----------|-----------|
| Determinism | Same input → identical output. No randomness. If random element exists, seed MUST be fixed. |
| External calls | MUST NOT call any API, database, or service |
| State | MUST NOT mutate shared state between invocations |
| Composition | Rules MUST be independently testable and composable |

#### Scenario: Determinism verification

- GIVEN a known set of metrics, edges, and risk data
- WHEN the engine is invoked twice with identical input
- THEN both outputs MUST be byte-identical

#### Scenario: Source unavailable

- GIVEN one source module (e.g., Edge Discovery) returns error or no data
- WHEN the engine runs
- THEN rules depending on that source produce `None`; remaining rules still evaluate

### Requirement: Rule Categories

The system MUST implement rules in at least four categories.

| Category | Minimum Rules | Pattern Examples |
|----------|--------------|-----------------|
| Performance | 2 | Win rate trend, expectancy vs profit factor divergence |
| Risk | 2 | Drawdown recovery, concentration risk |
| Edge | 2 | Significant edge detected, insufficient edge evidence |
| Composite | 1 | Cross-module synthesis (e.g., high edge + high drawdown) |

#### Scenario: Performance trend insight

- GIVEN 100+ trades with declining win rate and stable expectancy
- WHEN performance rules evaluate
- THEN output includes `category: "performance"` with trend direction and supporting period metrics

#### Scenario: Risk concentration insight

- GIVEN 80% of risk allocated to a single asset
- WHEN risk rules evaluate
- THEN output includes `category: "risk"` with concentration warning and asset exposure refs

#### Scenario: Edge insight with insufficient evidence

- GIVEN Edge Discovery returns "insufficient" confidence for a group
- WHEN edge rules evaluate
- THEN output includes `category: "edge"` with `confidence < 0.3` and `message` citing the insufficient evidence

### Requirement: API Endpoints

The system MUST expose three endpoints under `/api/ai-insights/`.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/summary` | GET | All current insights grouped by category |
| `/detail/{insight_id}` | GET | Single insight with full evidence chain |
| `/refresh` | POST | Re-run rule engine and replace cached insights |

#### Scenario: Full summary with all categories

- GIVEN Analytics + Risk + Edge data available
- WHEN `GET /api/ai-insights/summary`
- THEN response contains `observations[]` grouped by category AND `confidence_level`

#### Scenario: Refresh replaces cache

- GIVEN existing cached insights
- WHEN `POST /api/ai-insights/refresh`
- THEN 202 Accepted returned AND subsequent `/summary` reflects new results

#### Scenario: Source error on detail

- GIVEN `insight_id` references a metric from a now-unavailable source
- THEN `GET /api/ai-insights/detail/{id}` returns 200 with `message` citing the degraded source AND still displays cached data

### Requirement: AIInsightsService

The system MUST implement `AIInsightsService` that coordinates data collection and rule execution.

- Consumes `AnalyticsService`, `EdgeDiscoveryService` via DI — never calculators directly
- Calls existing service methods only, never re-fetches or re-computes analytics
- Returns `InsightResponse { observations: list[Insight], confidence_level: float }`

#### Scenario: Service composition

- GIVEN `AnalyticsService` provides summary metrics and `EdgeDiscoveryService` provides rankings
- WHEN `AIInsightsService.get_insights()` is called
- THEN it calls `get_summary()` + `get_rankings()`, passes to rule engine, and returns structured insights

### Requirement: Frontend Module

The frontend MUST include a page under `/analytics/insights` with components following existing module patterns.

| Component | Responsibility |
|-----------|---------------|
| `InsightList` | Lists all current insights by category |
| `InsightCard` | Single insight: message + severity + confidence |
| `EvidenceCitation` | Drill-down: supporting metric names + trade IDs |
| Hook | React Query wrapper for each endpoint |

#### Scenario: Loading state

- GIVEN insights are being fetched
- WHEN the page renders
- THEN skeleton cards (3) display per existing pattern

#### Scenario: Empty state

- GIVEN no data after refresh
- THEN page shows "Insufficient evidence — run more trades" with 0 observations

#### Scenario: Error state

- GIVEN API returns 5xx
- THEN ErrorFallback with retry button displays

## Acceptance Criteria

- [ ] Every `Insight` has `supporting_metrics[]` with ≥1 metric reference
- [ ] Every `Insight` has `supporting_trades[]` or `message` includes "no specific trades"
- [ ] Insufficient evidence → insight explicitly states insufficiency
- [ ] Rule engine never calls external APIs — verified by tests
- [ ] Rule engine deterministic — same input → identical output (test assertion)
- [ ] All existing tests pass with zero regressions
