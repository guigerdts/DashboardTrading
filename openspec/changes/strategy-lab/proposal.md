# Proposal: Strategy Lab — Scientific Experiment Framework (v1.6.0)

## Intent

Traders need to **test hypotheses about their strategies** without polluting the journal. Today you can't version a strategy, run it against historical data, compare two parameter sets, or prove one outperforms another — there's simply no mechanism. Strategy Lab adds a scientific experiment layer on top of the existing analytics engine, keeping every run reproducible months later.

## Scope

### In Scope (v1.6.0)
1. **StrategyVersion entity** — versioned parameters as JSON + rules_hash per strategy. Catalog itself stays untouched.
2. **Experiment + Run + RunMetric models** — immutable execution records. Experiment = hypothesis, Run = single execution, RunMetric = individual metric.
3. **Strategy Lab module** — `backend/app/modules/strategy_lab/` with CRUD + execution service.
4. **StrategyComparisonEngine** — bootstrap-based comparison (CI of difference + permutation test). Reuses `NumpyStatisticsEngine`.
5. **Run execution** — calls `AnalyticsService` with frozen filters, stores results immutably.
6. **Engine version capture** — records analytics engine version (git hash) per run.
7. **Frontend MVP** — Experiment list, Run detail with metrics, comparison view.

### Out of Scope
- Walk-forward execution (Phase 2)
- Strategy rules DSL (metadata-only versioning)
- Real-time execution
- Parameter search / optimization
- LLM or generative AI integration
- Modifications to Trade, Strategy, or Analytics models

## Capabilities

### New Capabilities
- `strategy-versioning`: versioned parameters + immutable snapshot per strategy
- `experiment-execution`: create experiments, define hypotheses, execute runs
- `run-comparison`: bootstrap-based statistical comparison between runs
- `engine-version-tracking`: capture analytics engine version at run time

### Modified Capabilities
- None. Existing capabilities (analytics, edge discovery, trade journal) remain unchanged.

## Approach

New `strategy_lab` module following the existing module pattern (models → schemas → service → router). Four new tables in `trading_journal.db`. Run execution is synchronous (pure calculation over `AnalyticsService`). Comparison reuses `NumpyStatisticsEngine` for bootstrap CI and adds a permutation test — no new statistical dependencies. Immutability enforced at the DB level (no UPDATE/DELETE on runs after completion).

**PR #1 — Data Layer** (~400 LOC): Models, migrations, repositories.
**PR #2 — Execution Engine** (~500 LOC): Run service, ComparisonEngine, version capture.
**PR #3 — API Layer** (~350 LOC): REST endpoints, integration tests.
**PR #4 — Frontend** (~450 LOC): Pages, components, hooks, tests.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/models/` | New | 4 model files + `__init__.py` export |
| `backend/app/modules/strategy_lab/` | New | Service, schemas, router, comparison engine |
| `backend/app/db/unit_of_work.py` | Modified | Add Strategy Lab repositories |
| `backend/alembic/versions/` | New | Migration for 4 tables |
| `frontend/src/` | New | Experiment list, run detail, comparison pages |
| `backend/app/modules/analytics/` | Unchanged (imported) | Reused via interface only |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Scope creep on stats comparison (Bayesian, MCMC etc.) | Medium | Scoped to bootstrap CI + permutation test only. ADR when adding new tests. |
| Engine version capture has no existing mechanism | Low | Read `importlib.metadata` or `git rev-parse HEAD` at service startup. Fallback to "unknown". |
| `list_closed()` filters by exit_datetime, not entry | Low | Document in spec. This is correct for PnL analysis but surprises new users. |
| Seed stability across numpy versions | Low | Document in user docs. Store seed per run in params. |

## Rollback Plan

- **Before PR #1 merges**: drop new tables, revert migration, delete `strategy_lab/` module.
- **After merge**: reverse migration (`alembic downgrade -1`), delete module + revert `unit_of_work.py`, revert frontend changes.
- Data loss: only experiment data (no journal data touched). Acceptable for a new feature.

## Dependencies

- Existing `AnalyticsService` and `AnalyticsFilter` (reused, not changed)
- `NumpyStatisticsEngine` from edge discovery (imported, not changed)
- `TradeRepository.list_closed()` with date filtering
- No new pip packages required (numpy, scipy already available)

## Success Criteria

- [ ] Can create a StrategyVersion with JSON parameters from an existing Strategy
- [ ] Can create an Experiment, execute a Run, and view metrics in under 2s
- [ ] Can compare two Runs and get bootstrap CI + permutation p-value
- [ ] Run is immutable after completion (no UPDATE/DELETE allowed)
- [ ] Engine version captured and displayed per run
- [ ] All existing analytics tests continue to pass unchanged
- [ ] Tests: 80%+ coverage on strategy_lab module
