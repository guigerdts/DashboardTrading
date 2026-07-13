# Proposal: v1.5.0 — AI Insights

## Intent

Move from **"what happened"** (analytics metrics) to **"what does this mean for my trading"** (structured interpretation). A deterministic rule engine consumes existing validated evidence from Analytics, Risk Analytics, and Edge Discovery — never invents data, never calculates metrics. Every insight cites its supporting metrics and trades (ADR-008). When evidence is insufficient, the engine explicitly says so.

## Scope

### In Scope

| # | Deliverable | Description |
|---|-------------|-------------|
| 1 | **Risk Analytics wiring** | Router endpoints + service methods + schemas for the 3 existing calculators (`risk.py`, `exposure.py`, `correlation.py`). No new metrics. |
| 2 | **Rule Engine core** | Pure Python deterministic engine. Each rule is a standalone function: `(metrics, edges) → Optional[Insight]`. Rules are composable, independently testable. |
| 3 | **Insight schemas** | Pydantic models for structured insights: `supporting_metrics[]`, `supporting_trades[]`, `confidence`, `recommendation`. Zero free-text. |
| 4 | **API layer** | `GET /api/analytics/insights` — collects all analytics → runs rule engine → returns structured insights. |
| 5 | **Frontend module** | `/analytics/insights` page with components for displaying insights, evidence citations, drill-down to source metrics/trades. |

### Out of Scope

- LLM integration (local or external) — deferred to v2+
- New analytics metrics or calculators
- Changes to existing Pydantic models or API contracts
- Real-time or streaming insights
- Natural language generation
- Edge Discovery engine changes

## Capabilities

### New

- `ai-insights`: Deterministic rule engine + insight API + frontend module. Consumes Analytics, Risk Analytics, and Edge Discovery outputs.

### Modified

- `risk-analytics` (delta): Add wiring layer — `risk-metrics`, `exposure/*`, `correlation` endpoints + service methods + schemas. Calculators already exist; only the API surface is new.

## Architecture Approach

```
┌────────────────────────────────────────────────────────────┐
│  Layer 1 — Data Collection (AIInsightsService)             │
│  Calls existing service methods, never calculators directly │
│  → AnalyticsService.get_summary(), .get_breakdown_*()       │
│  → AnalyticsService.get_risk_metrics(), .get_exposure_*()   │
│  → EdgeDiscoveryService.get_rankings()                      │
├────────────────────────────────────────────────────────────┤
│  Layer 2 — Rule Engine (pure functions, no AI deps)        │
│  ┌─────────────┐ ┌──────────────┐ ┌──────────────────┐     │
│  │ trend_rules │ │ edge_rules   │ │ risk_rules       │     │
│  │ .win_rate() │ │ .quality()   │ │ .drawdown()      │     │
│  │ .expectancy │ │ .regression()│ │ .concentration() │     │
│  └─────────────┘ └──────────────┘ └──────────────────┘     │
│           └──────→ RuleEngine.evaluate(all_data) ←──────┘  │
├────────────────────────────────────────────────────────────┤
│  Layer 3 — Output (structured, traceable)                  │
│  InsightResponse { observations[], confidence_level }      │
│  Each observation: metric_ref, trade_ids[], recommendation │
├────────────────────────────────────────────────────────────┤
│  Layer 4 — Frontend                                        │
│  InsightList → InsightCard → EvidenceCitation → Drilldown  │
└────────────────────────────────────────────────────────────┘
```

**Key decisions**:
- **Module isolation**: `backend/app/modules/ai_insights/` — never imports calculators directly, only consumes via service layer
- **No duplication**: Data collection calls existing service methods; rules analyze pre-computed outputs
- **Determinism guarantee**: No randomness, no external calls, no state between invocations
- **Traceability**: Every `InsightObservation` must carry `supporting_metrics[]` (metric name + value) and `supporting_trades[]` (trade IDs), enforced at schema level

## User Experience

| State | What user sees | Behavior |
|-------|---------------|----------|
| **No data** | "Insufficient evidence — run more trades" | Engine returns 0 observations |
| **Rules triggered** | Insight cards grouped by category (Trends, Edges, Risk) | Each card shows recommendation + evidence citation |
| **Evidence drill-down** | Click metric → source analytics chart | Linked by metric name + filter |
| **Edge insight** | "Strategy X × Setup Y shows significant edge" | Cites EdgeScore with CI, p-value, stability |
| **Loading** | Skeleton cards (3) | Per existing pattern |
| **Error** | ErrorFallback + retry | Matches existing module convention |

## PR Slicing (Stacked-to-Main)

| PR | Focus | Est. LOC | Risk |
|----|-------|----------|------|
| **PR #1** | Risk Analytics wiring — 5 endpoints, service methods, schemas, integration tests | ~400 | Low — additive, calculators exist |
| **PR #2** | Rule Engine core — engine interface, rule functions, insight schemas, unit tests | ~450 | Medium — rule design quality |
| **PR #3** | API Layer — AIInsightsService, router, integration tests, snapshot regression | ~350 | Low — thin orchestrator |
| **PR #4** | Frontend — page, InsightList, InsightCard, EvidenceCitation, hooks, tests | ~500 | Medium — new module pattern |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Rule false positives (misleading insights) | Medium | Statistical gates on every rule — no insight below configurable confidence threshold |
| Rule gap — no insight returned for valid patterns | Medium | Transparent — engine logs which rules ran and why they didn't fire |
| Risk Analytics frontend expects extended metrics not in wiring | Low | Document mismatch in PR #1 — frontend components use subset of fields; non-breaking |
| Schema drift between analytics outputs and rule expectations | Low | Rules consume validated Pydantic models — compiler catches mismatches |

## Rollback Plan

Revert the commit. Each PR is additive — no schema migrations, no contract changes to existing modules. AI Insights module is self-contained: revert `ai_insights/` + removed router lines.

## Dependencies

- **Python**: No new dependencies. Rule engine uses stdlib + existing `pydantic`.
- **Frontend**: No new npm packages. Uses existing `@tanstack/react-query`, `recharts`, `lucide-react`.
- **Pre-existing**: 3 risk calculators already built. Edge Discovery engine fully implemented.

## Success Criteria

- [ ] Risk Analytics wiring: 5 new endpoints return data matching existing calculators output
- [ ] All existing tests pass with zero regressions
- [ ] Rule engine: same input → identical output (determinism verified in tests)
- [ ] Every insight observation includes `supporting_metrics[]` and `supporting_trades[]` with valid data
- [ ] Empty trade list → 0 observations, "insufficient evidence" response
- [ ] Frontend renders loading → empty → success → error states per module convention
- [ ] Snapshot regression tests: known analytics input → expected insight output
