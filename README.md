# DashboardTrading — Trade Intelligence Platform (TIP)

Professional trading intelligence platform for tracking, analyzing, and improving trading performance. Offline-first, modular, and incrementally built.

**Stack:** Python 3.12+ · FastAPI · React 18 · Vite · SQLite  
**Methodology:** SDD (Spec-Driven Development) — each feature is proposed, specified, designed, implemented, verified, and archived.

---

## Current Version: v1.1.0 — Analytics Dashboard

Full analytics dashboard with 7 KPI summary cards, equity chart, asset/direction breakdowns, breakdown tables by strategy/setup/tag/mistake, R-multiple distribution histogram, and day×hour trading activity heatmap.

---

## Version History

| Version | Release | What |
|---------|---------|------|
| v1.1.0 | current | **Analytics Dashboard** — KPI cards, breakdowns, R histogram, heatmap |
| v1.0.0 | 2026-07 | **Trade Context Classification** — Strategy, Setup, Tag, Mistake catalogs + assignment |
| v0.9.0 | 2026-07 | **Trade Detail & Review** — enriched trade view, review editor |
| v0.8.0 | 2026-07 | **Trading Journal MVP** — filtered/sorted table, summary cards, pagination |
| v0.7.0 | 2026-07 | **MT5 Import (Frontend)** — import UI, preview, confirm, error handling |
| v0.6.1 | 2026-07 | **Analytics Backend Recovery** — calculator rebuild, stash recovery |
| v0.6.0 | 2026-07 | **Dashboard UI** — filter bar, summary, equity, breakdown widgets |
| v0.5.0 | 2026-07 | **Analytics** — backend calculators, summary, equity, breakdown endpoints |
| v0.4.0 | 2026-07 | **MT5 Import** — MT5 file parsing, validation, preview, confirm flow |
| v0.3.0 | 2026-07 | **Application Layer** — services, routes, frontend skeleton |
| v0.2.0 | 2026-07 | **Domain Model** — trades, accounts, transactions, categories |
| v0.1.0 | 2026-07 | **Base Architecture** — FastAPI + React scaffolding, SQLite, Alembic |

---

## Architecture

```
DashboardTrading/
├── backend/                    # FastAPI application (Python)
│   ├── app/
│   │   ├── modules/            # Domain modules (accounts, analytics, trades, etc.)
│   │   ├── shared/             # Shared utilities, base classes
│   │   └── main.py             # Application entry point
│   ├── tests/                  # Backend test suite
│   ├── alembic/                # Database migrations
│   └── pyproject.toml
├── frontend/                   # React SPA (JavaScript, Vite)
│   ├── src/
│   │   ├── modules/            # Feature modules (analytics, catalogs, trades, etc.)
│   │   ├── shared/             # Shared components, hooks, utilities
│   │   ├── api/                # API client layer
│   │   └── test/               # Frontend test setup
│   └── package.json
├── data/                       # SQLite database (runtime)
├── assets/                     # User assets (screenshots, icons, logos, themes)
├── openspec/                   # OpenSpec SDD artifacts
│   ├── config.yaml
│   └── specs/                  # Main domain specs
└── .sdd/                       # Engram-based SDD artifacts (proposals, designs, tasks)
```

### Core modules (backend)

| Module | Responsibility |
|--------|---------------|
| `trades` | Trade CRUD, enriched detail, review sub-resource |
| `analytics` | Calculators, breakdowns, distribution, heatmap, summary |
| `catalogs` | Strategy, Setup, Tag, Mistake CRUD + pivot sync |
| `imports` | MT5 trade file import pipeline |
| `accounts` | Trading accounts management |
| `dashboard` | Dashboard data aggregation |

### Core modules (frontend)

| Module | Responsibility |
|--------|---------------|
| `analytics` | DashboardPage with KPIs, charts, breakdowns, heatmap |
| `catalogs` | Admin pages for strategies/setups/tags/mistakes |
| `trades` | Trading journal table, trade detail, context selectors |
| `imports` | MT5 import wizard (upload, preview, confirm) |
| `trade-review` | Trade review editor |

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- npm
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Setup

```bash
# Install all dependencies
make install

# Start development servers
make dev
# Backend: http://localhost:8000
# Frontend: http://localhost:5173
```

### Available Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all backend and frontend dependencies |
| `make dev` | Start backend (:8000) and frontend (:5173) dev servers |
| `make lint` | Lint backend (ruff) and frontend (eslint) |
| `make test` | Run backend (pytest) and frontend (vitest) tests |
| `make test-backend` | Run backend tests only |
| `make test-frontend` | Run frontend tests only |
| `make format` | Format backend code (ruff) |
| `make db-migrate` | Run pending Alembic migrations |

---

## SDD Workflow

This project uses Spec-Driven Development (SDD) — each feature follows:

```
Discovery → Proposal → Spec → Design → Tasks → Apply → Verify → Archive
```

All artifacts are persisted in Engram (cross-session memory) and optionally mirrored to `openspec/` for team sharing.

**Tooling integrated into SDD:**
- **CodeGraph** — structural code exploration before writing (reuse detection, pattern matching)
- **Context7** — framework/library documentation lookup (React Query, Recharts, FastAPI)

---

## Testing

- **Backend:** pytest (75+ tests) — services, repositories, calculators, schemas
- **Frontend:** vitest + Testing Library (55+ tests) — components, hooks, loading/empty/error states
- Pre-commit hook runs GGA (Gentle Guardian Angel) code review on staged files

---

## Roadmap

| Version | Focus | Scope |
|---------|-------|-------|
| **v1.2.0** 🎯 next | **Equity & Performance Analytics** | Equity curve, drawdown, rolling metrics, period comparison, CSV/Excel export |
| **v1.3.0** | **Risk Analytics** | Risk of ruin, MAE/MFE, holding time, exposure, session distribution |
| **v1.4.0** | **Edge Discovery** | Cross-analysis of Strategy×Setup×Tag×Mistake with statistical validation |
| **v1.5.0** | **AI Insights** | Automated summaries, pattern detection, natural-language recommendations |

### Design principles for future versions

- **No schema migrations unless strictly necessary** — analytics layers must operate on existing data
- **Quantitative base first, AI later** — v1.5 builds on v1.2–v1.4 statistical foundation
- **Edge Discovery (v1.4)** requires minimum-observations filter + bootstrap CI 95% before ranking
- **IA nunca suple métricas que aún no existen**

---

## Tags

All releases are tagged in git:

```bash
git tag --sort=-v:refname
```

Check the latest releases for changelogs and migration notes.
