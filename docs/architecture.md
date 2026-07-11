# Architecture

## Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Backend | Python 3.12+ · FastAPI | REST API, domain logic, calculations |
| Frontend | React 18 · Vite · Tailwind CSS | SPA user interface |
| Database | SQLite via SQLAlchemy + Alembic | Offline-first persistent storage |
| Testing | pytest (backend) · vitest + Testing Library (frontend) | Automated verification |

---

## Backend Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory, CORS, lifespan
│   ├── modules/                 # Domain modules
│   │   ├── trades/              # Trade CRUD, enriched detail, reviews
│   │   ├── analytics/           # Calculators, breakdowns, heatmap, equity
│   │   ├── dashboard/           # Dashboard aggregation
│   │   ├── catalogs/            # Strategy/Setup/Tag/Mistake CRUD + sync
│   │   ├── imports/             # MT5 import pipeline
│   │   ├── accounts/            # Trading accounts
│   │   ├── assets/              # Asset/symbol management
│   │   ├── settings/            # User configuration
│   │   ├── strategies/          # Strategy management
│   │   ├── setups/              # Setup management
│   │   ├── risk_management/     # Risk metrics
│   │   ├── psychology/          # Psychology tracking
│   │   ├── screenshot_library/  # Screenshot management
│   │   └── error_management/    # Error tracking
│   ├── shared/                  # Shared lib: base repository, pagination, errors
│   └── __init__.py
├── tests/                       # pytest test suite
├── alembic/                     # Database migrations
├── data/                        # SQLite database files
├── scripts/                     # Utility scripts
└── pyproject.toml               # Dependencies and tool config
```

### Module pattern

Each domain module follows a consistent layered architecture:

```
modules/{name}/
├── schemas.py          # Pydantic models (request/response)
├── models.py           # SQLAlchemy ORM models
├── repository.py       # Database access layer
├── service.py          # Business logic
├── router.py           # FastAPI route definitions
└── calculators.py      # Domain calculations (analytics module)
```

---

## Frontend Structure

```
frontend/src/
├── main.jsx                    # App entry point
├── App.jsx                     # Root component, route definitions
├── pages/                      # Page-level components (lazy-loaded)
├── modules/                    # Feature modules
│   ├── analytics/              # Dashboard, KPIs, charts, breakdowns, heatmap
│   │   ├── pages/              # DashboardPage
│   │   ├── components/         # SummaryCards, BreakdownTable, RHistogram, HeatmapChart
│   │   ├── hooks/              # useSummary, useEquity, useBreakdown*, useRDistribution, useHeatmap
│   │   ├── services/           # analyticsApi
│   │   └── utils/              # formatters, constants
│   ├── catalogs/               # Strategy/Setup/Tag/Mistake admin pages
│   ├── trades/                 # Journal table, trade detail
│   ├── imports/                # MT5 import wizard
│   └── trade-review/           # Review editor
├── shared/                     # Shared components (ErrorBoundary, Skeleton, api client)
├── api/                        # Base API client
└── test/                       # Test setup (jest-dom matchers, mocks)
```

### Data flow

```
React Component → React Query Hook → analyticsApi → fetch API → FastAPI Router → Service → Repository → SQLite
                                                          ↓
                                                    Calculator (domain)
                                                          ↓
                                                    Response ← Pydantic
```

Filters are synced via URL search params (`useDashboardFilters`).` All API calls pass `account_id`, `date_from`, `date_to` when present.

---

## Key Architecture Decisions

### ADR-001: In-memory calculators, not SQL aggregations
Analytics calculations (PnL, equity, drawdown) run in Python, not SQL. Trade-off: more memory per request, but testable, composable, and versionable. SQL aggregations are used only for trivial counts/sums.

### ADR-002: React Query for server state
All API data flows through `@tanstack/react-query`. No Redux, no global state for server data. URL search params are the single source of truth for filter state.

### ADR-003: Offline-first with SQLite
SQLite is the production database. No separate PostgreSQL/MySQL server. Migrations via Alembic. Trade-off: no horizontal scaling, but zero operational overhead for single-user/small-team use.

### ADR-004: No ORM for analytics queries
Analytics reads use raw SQL via SQLAlchemy `text()` for complex aggregations. ORM is used for CRUD operations only.

### ADR-005: SDD with Engram persistence
All SDD artifacts are persisted in Engram (cross-session memory). The `.sdd/` directory mirrors Engram topics for reference. `openspec/` is used for specs only.

---

## Cross-cutting Concerns

| Concern | Approach |
|---------|----------|
| Error handling | `ErrorBoundary` per widget, structured API errors, `@gap` markers for unimplemented endpoints |
| Pagination | Offset-based, configurable per endpoint |
| Loading states | `Skeleton` component per widget, React Query `isLoading/isFetching` |
| Empty states | Each component handles `data === null/undefined/[]` explicitly |
| Filtering | URL search params, debounced account ID, immediate date filter |
