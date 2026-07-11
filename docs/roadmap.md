# Roadmap

## Current Version: v1.1.0 — Analytics Dashboard (released)

Full analytics dashboard with 7 KPI summary cards, equity chart, asset/direction breakdowns, breakdown tables by strategy/setup/tag/mistake, R-multiple distribution histogram, and day×hour trading activity heatmap.

---

## Completed Cycle

| Version | Description | What was built |
|---------|-------------|----------------|
| v0.1.0 | Base Architecture | FastAPI + React scaffolding, SQLite, Alembic migrations, project structure |
| v0.2.0 | Domain Model | Trade, Account, Transaction, Category models with relationships and tests |
| v0.3.0 | Application Layer | Service layer, REST routes, frontend skeleton with lazy loading |
| v0.4.0 | MT5 Import | MT5 file parser, validation, preview, confirm pipeline, 10 acceptance criteria |
| v0.5.0 | Analytics Backend | PnL calculators, summary, equity curve, asset/direction breakdown endpoints |
| v0.6.0 | Dashboard UI | Filter bar, SummaryCards, EquityChart, breakdown widgets, Recharts integration |
| v0.6.1 | Analytics Recovery | Calculator rebuild from stashes, full test coverage recovery |
| v0.7.0 | MT5 Import Frontend | Upload UI, navigation machine, error display, 45+ frontend tests |
| v0.8.0 | Trading Journal MVP | Filtered/sorted table, summary cards, pagination, backend sort/search/summary |
| v0.9.0 | Trade Detail & Review | Enriched trade detail endpoint, review editor (frontend + backend) |
| v1.0.0 | Trade Context Classification | Strategy/Setup/Tag/Mistake catalogs + pivot sync, admin pages |
| v1.1.0 | Analytics Dashboard | KPI cards (7), BreakdownTable, RHistogram, HeatmapChart, 55 frontend tests |

---

## Next Up: v1.2.0 — Equity & Performance Analytics

### Objective
Build the Equity & Performance Analytics layer without schema changes, reusing the existing analytics infrastructure.

### Domain scope
- Equity curve (realized PnL only)
- Drawdown (absolute, percentage, maximum)
- Rolling metrics (win rate, profit factor, expectancy, average R) — 30-trade window by default
- Performance by period (monthly, quarterly, yearly)
- Period comparison (two arbitrary ranges, absolute + percentage deltas)
- CSV/Excel export (if architecture permits)

### Key decisions
- **Equity:** closed trades only. Open trades shown separately as independent KPI.
- **Drawdown:** based on realized equity curve.
- **Rolling window:** 30 trades (not days). Configurable per metric.
- **Small samples:** show "Insufficient data" below minimum threshold. Never interpolate.
- **Architecture:** zero migrations, zero new entities. Reuse existing calculators and filters.

---

## Future Versions

### v1.3.0 — Risk Analytics

- Risk of Ruin
- Consecutive Wins/Losses
- MAE/MFE (Maximum Adverse/Favorable Excursion)
- Holding Time Analysis
- Exposure metrics
- Session-based distribution

### v1.4.0 — Edge Discovery

- Cross-analysis of Strategy × Setup × Tag × Mistake combinations
- Ranking with statistical validation (minimum observations configurable, bootstrap CI 95%)
- Show uncertainty, not just point estimates
- Mark under-sampled combinations as "Insufficient data"
- Architecture prepared for False Discovery Rate correction

### v1.5.0 — AI Insights

- Automated trading summaries
- Pattern detection
- Recommendations
- Natural-language explanations

---

## Design Principles

1. **Metrics first, AI later** — v1.5 builds on v1.2–v1.4. AI never substitutes metrics that don't exist.
2. **No schema migrations unless necessary** — analytics operate on existing data.
3. **Small, verifiable increments** — each version is one focused capability, fully tested and archived.
4. **Edge Discovery must be statistically sound** — no ranking without minimum observations + confidence interval.
5. **CodeGraph before writing, Context7 only for framework doubts.**

---

## Tag History

```bash
v1.1.0-analytics-dashboard
v1.0.0-trade-context-classification
v0.9.0-trade-detail-review
v0.8.0-trading-journal-mvp
v0.7.0-mt5-import-frontend
v0.6.1-analytics-backend-recovery
v0.6.0-dashboard-ui
v0.5.0-analytics
v0.4.0-mt5-import
v0.3.0-application-layer
v0.2.0-domain-model
```

All tags follow `v<major>.<minor>.<patch>-<descriptor>`.
