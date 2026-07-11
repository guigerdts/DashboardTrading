# Proposal: v1.4.0 — Edge Discovery

## Intent

Discover statistically valid trading edges across Strategy × Setup × Session × Asset × Direction, plus Tag and Mistake impact. Every edge carries bootstrap CI, FDR, stability — under a composable `EdgeScore` contract for frontend and v1.5 AI.

## Scope

### In Scope
- Multi-dimension ranking (Strategy × Setup × Session × Asset × Direction)
- Tag impact / Mistake impact / Condition-drawdown analysis
- Bootstrap CI (95%) + FDR (Benjamini-Hochberg) on all rankings
- Split-half stability test
- `StatisticsEngine` interface — numpy isolated behind it
- Generation/query separation — engine computes, endpoints read
- `EdgeScore` contract (10 fields, per Adjustment 3)
- Traceability: Edge → Group → trade IDs
- Min 30 observations per combo

### Out of Scope
- AI/ML, predictions, recommendations, real-time computation, schema migrations

## Capabilities

### New
- `edge-discovery`: Cross-dimension engine with bootstrap, FDR, stability, EdgeScore. Backend + query endpoints + frontend.

### Modified
None — additive within analytics module.

## Approach

Three architectural decisions from adjustments:
1. **StatisticsEngine interface** — Abstract class (`bootstrap_ci`, `fdr_correct`, `stability_test`). `NumpyStatisticsEngine` first impl. Calculators depend on the interface, never on numpy.
2. **Generation/query split** — `EdgeDiscoveryEngine` fetches trades → enumerates combos → bootstraps → FDR → scores → stores. Endpoints read cached results only. No per-request recomputation.
3. **EdgeScore contract** — 10-field canonical schema for v1.4 frontend and v1.5 AI.

Existing patterns preserved: stateless calculators, AnalyticsService, React Query.

## Affected Areas

| Area | Impact |
|------|--------|
| `calculators/edge_discovery.py` | New — enumeration + grouping |
| `calculators/statistics_engine.py` | New — abstract + numpy impl |
| `calculators/stability.py` / `fdr.py` | New |
| `schemas.py` | Extended — EdgeScore, EdgeResponse |
| `service.py` / `router.py` | Extended — EdgeDiscoveryService, GET /analytics/edges |
| `EdgeRankingTable.jsx` | New |
| `analyticsApi.js` / `QUERY_KEYS.js` | Extended |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| numpy first non-stdlib dep | Medium | Isolated behind StatisticsEngine |
| Bootstrap × hundreds combos CPU-bound | High | Async generation + cached results |
| New engine, not additive | Medium | Follows existing module patterns |

## Rollback Plan

Revert the commit. No migrations, no schema changes. Edge cache is ephemeral.

## Dependencies

`numpy>=1.26` (behind StatisticsEngine interface). No others.

## Success Criteria

- [ ] All existing tests pass with no regressions
- [ ] Bootstrap CI matches manual percentile calc for known dataset
- [ ] FDR correctly filters below-threshold combos
- [ ] Edges with < 30 trades show `confidence_level: "insufficient"`
- [ ] Generation writes cache; endpoints return cached data only
- [ ] Zero numpy imports outside StatisticsEngine implementation
- [ ] EdgeScore contract matches all 10 fields verbatim
