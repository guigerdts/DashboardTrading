## Exploration: Trade Intelligence Platform — Base Architecture

### Current State

Greenfield project at `/root/DashboardTrading`. The repository exists with:
- `openspec/` directory (config, empty specs/ and changes/ with archive/)
- `.atl/` directory (skill registry)
- Short `README.md` describing the project as "Plataforma profesional de inteligencia para trading. Stack: Python, FastAPI, React, SQLite. Offline-first, modular, escalable."
- No source code, no dependencies, no build configuration yet.

### Affected Areas

```
/root/DashboardTrading/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # App factory, lifespan, CORS
│   │   ├── config.py            # Pydantic Settings
│   │   ├── database.py          # Async engine + session factory
│   │   ├── dependencies.py      # Shared DI (get_db, etc.)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── router.py        # Root router aggregation
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py    # v1 prefix router
│   │   │       ├── health.py    # Health check endpoint
│   │   │       └── trades.py    # Placeholder trades CRUD
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── base.py          # DeclarativeBase
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── common.py        # Shared Pydantic models
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   └── trade.py         # Placeholder trade service
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── base.py          # Abstract CRUD repository
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── uv.lock
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       └── test_health.py
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/
│   │   │   └── client.ts        # Axios/ky instance
│   │   ├── hooks/
│   │   │   └── useHealth.ts     # TanStack Query hook
│   │   ├── store/
│   │   │   └── index.ts         # Zustand store
│   │   ├── components/
│   │   │   └── ui/              # shadcn/ui components
│   │   ├── pages/
│   │   │   └── Dashboard.tsx
│   │   ├── lib/
│   │   │   └── utils.ts
│   │   └── types/
│   │       └── api.ts
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── package.json
│   └── tests/
├── .gitignore
├── .pre-commit-config.yaml
├── Makefile
└── README.md
```

### Approaches

1. **Monorepo (backend/ + frontend/ in same repo)** — Both Python backend and React frontend in a single repository with clear separation.
   - Pros: Single git history, shared CI/CD, atomic commits across stack, easier onboarding, one `make dev` to run everything
   - Cons: Larger repo size, both ecosystems in one place, tighter coupling risk
   - Effort: Low (no cross-repo orchestration needed)

2. **Separate repos (backend/ + frontend/ as independent repos)** — Two distinct repositories.
   - Pros: Independent release cycles, separate CI/CD, focused issue tracking
   - Cons: Coordinated changes require two PRs, shared types duplication, extra tooling for dev workflow
   - Effort: Medium (need to manage cross-repo coordination)

3. **Flat structure (no separation)** — Everything at the root level.
   - Pros: Simplest to start
   - Cons: Unmaintainable as it grows, no clear boundaries, no scaling path
   - Effort: Low initially, very high later

### Technology Comparison Tables

#### Dependency Management

| Aspect | Poetry | uv |
|--------|--------|----|
| Speed (cold install) | ~45s | ~3s |
| Speed (resolution) | ~22s | ~1.4s |
| Python version mgmt | ❌ needs pyenv | ✅ built-in |
| Workspaces/monorepo | ❌ | ✅ |
| PEP 621 | ⚠️ limited | ✅ full |
| Publishing | ✅ built-in | ⚠️ needs twine |
| Maturity | 5+ years | 2+ years (OpenAI-backed) |

**Recommendation**: **uv** — 10-100x faster, built-in Python version management, workspace support for future monorepo needs, single binary replaces pyenv+pip+pipx+virtualenv.

#### ORM Choice

| Aspect | SQLAlchemy 2.0 (async) | SQLModel |
|--------|------------------------|----------|
| Maturity | Very high (15+ years) | Medium (3+ years) |
| Async support | ✅ native (create_async_engine) | ✅ via SQLAlchemy |
| Pydantic integration | ⚠️ manual mapping | ✅ unified models |
| Migration tooling | ✅ Alembic (native) | ✅ Alembic (via SQLAlchemy) |
| Flexibility | Very high | Good (SA subset) |
| Learning curve | Steep | Moderate |
| Team scalability | Good | Better (single source of truth) |

**Recommendation**: **SQLAlchemy 2.0 async** with **aiosqlite** driver. SQLModel is tempting for greenfield FastAPI but the unified model approach introduces coupling between DB models and API schemas that becomes problematic as the domain grows. SA 2.0's `Mapped` / `mapped_column` style is clean enough, and we need the full flexibility for future ML/analytics features.

#### Frontend Build Tool

| Aspect | Vite | Next.js (App Router) |
|--------|------|---------------------|
| Bundle size | ~500KB baseline | ~80KB + server |
| SSR/SSG | ❌ (not needed for SPA) | ✅ (overkill here) |
| Dev speed | Instant HMR | Fast HMR |
| Setup complexity | Low | Medium |
| Routing | React Router 7 | File-based (App Router) |
| Best for | SPAs, dashboards | Full-stack, SEO, content |

**Recommendation**: **Vite 8** — CRA was deprecated in Feb 2025. Next.js adds unnecessary complexity for a local-first SPA dashboard. Vite is the standard for React SPAs in 2026.

#### State Management

| Aspect | Zustand | Redux Toolkit | React Context |
|--------|---------|---------------|---------------|
| Bundle size | ~1KB gzip | ~11KB gzip | 0 (built-in) |
| Boilerplate | Minimal (create + hook) | Medium (slice + store) | Low |
| Performance | ✅ granular subscriptions | ✅ via selectors | ❌ whole-tree re-renders |
| DevTools | ⚠️ basic | ✅ time-travel | ❌ |
| Async patterns | ✅ plain async | ✅ createAsyncThunk | ❌ manual |
| Learning curve | Very low | Medium | Low |

**Recommendation**: **Zustand** for client state + **TanStack Query** for server state. Zustand is the 2026 standard for lightweight global state in React SPAs. Pair it with TanStack Query for API data caching, background refetching, and optimistic updates — eliminates most boilerplate Redux would need.

#### UI Component Library

| Aspect | shadcn/ui | MUI | Mantine |
|--------|-----------|-----|---------|
| Model | Copy-paste (own code) | npm dependency | npm dependency |
| Bundle impact | Only used components | Full library | Full library |
| Customization | Full (you own the code) | Theme-based | Theme-based |
| Tailwind | ✅ native | ❌ (Emotion/styled) | ❌ (CSS-in-JS) |
| Dashboard fit | ✅ DataTable, charts blocks | ✅ DataGrid, charts | ✅ DataTable |
| Version lock | ✅ never (you own it) | ❌ upgrade hell | ❌ upgrade hell |

**Recommendation**: **shadcn/ui** + **Tailwind CSS 4**. It's the dominant choice for 2026 dashboards. The copy-paste model means no dependency lock-in, full customization, and you only include what you use. Pair with **Recharts** for charting (line, bar, area, pie — sufficient for trading metrics).

#### Testing

| Layer | Tool | Why |
|-------|------|-----|
| Python unit/integration | pytest + httpx + pytest-asyncio | Standard for FastAPI |
| Python coverage | pytest-cov | Simple, well-integrated |
| React unit | vitest (built into Vite) | Zero-config, fast, Jest-compatible |
| React component | @testing-library/react | DOM-based testing, not implementation |
| E2E | Playwright (later phase) | Industry standard |

### Recommended Tech Stack

| Category | Choice | Version |
|----------|--------|---------|
| Python runtime | CPython | 3.12+ |
| Dependency manager | uv | latest |
| Web framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy 2.0 async | 2.0+ |
| Async DB driver | aiosqlite | 0.20+ |
| Migrations | Alembic | 1.13+ |
| Validation | Pydantic v2 | 2.0+ |
| Linting/formatting | ruff | latest |
| Runtime server | uvicorn | 0.30+ |
| React | React | 19 |
| Build tool | Vite | 6+ |
| TypeScript | TypeScript | 5.5+ |
| State (client) | Zustand | 5+ |
| State (server) | TanStack Query | 5+ |
| API client | ky (or axios) | latest |
| UI components | shadcn/ui + Tailwind CSS 4 | latest |
| Charts | Recharts | 2+ |
| CSS | Tailwind CSS | 4 |
| TS/JS linting | eslint + prettier | latest |

### Key Design Decisions

1. **Async SQLAlchemy with aiosqlite**: SQLite's single-writer limitation is real, but mitigated by WAL mode (`PRAGMA journal_mode=WAL`) which allows concurrent reads + one writer. For a personal/local-first trading journal (not a high-throughput API), this is more than sufficient. The async engine prevents blocking the event loop during DB operations.

2. **Repository pattern**: Abstract `BaseRepository[T]` with generic CRUD methods, then domain-specific repositories. This keeps DB access testable and swappable.

3. **Vite proxy for dev**: Vite dev server proxies `/api/*` to `http://localhost:8000`. No CORS issues in development. In production, FastAPI and the built frontend can be served from the same origin or with proper CORS middleware.

4. **Project structure**: `app/` follows the layered architecture pattern: `api/routers` → `services` → `repositories` → `models`. Each domain (trades, dashboard, strategy, risk) will be a module within these layers.

5. **uv workspaces**: Ready for future monorepo expansion (e.g., if we add ML service, CLI tool, etc.)

6. **No Docker for MVP**: Docker adds complexity that isn't justified for a local-first app. We use `uv run` + `npm run dev`. Docker can be added in a later phase for deployment.

### Dev Workflow

```
make install          # Backend: uv sync | Frontend: npm install
make dev              # Run both servers (uvicorn + vite simultaneously)
make lint             # ruff check backend/ | eslint frontend/
make format           # ruff format backend/ | prettier frontend/
make test             # pytest backend/ | vitest run frontend/
make db-init          # alembic init migrations
make db-migrate       # alembic revision --autogenerate
make db-upgrade       # alembic upgrade head
```

Suggested `Makefile` strategy:
- `.phony` targets that delegate to backend/ or frontend/ commands
- `make dev` uses a simple parallel approach: `uv run uvicorn app.main:app --reload` in backend/ and `npm run dev` in frontend/
- Could use `concurrently` npm package for unified output stream

### CORS Strategy

- **Development**: Vite proxy (`server.proxy` in `vite.config.ts`) forwards `/api` to FastAPI. No CORS headers needed.
- **Production**: FastAPI's `CORSMiddleware` with explicit allowed origins, or serve frontend static files from FastAPI for same-origin simplicity.

### Risks

1. **SQLite concurrency limits**: If the app grows beyond single-user or concurrent write patterns, SQLite will bottleneck. Mitigation: WAL mode, connection pooling. Future: migrate to PostgreSQL.
2. **No Docker means environment drift**: Different Python/Node versions locally. Mitigation: `.python-version` + `nvmrc` + uv's Python management.
3. **uv vs Poetry maturity gap**: uv is newer; some edge cases may surface. Mitigation: uv is backed by Astral (now OpenAI), has 2+ years of production use, and this is a greenfield project — no migration cost.
4. **shadcn/ui dependency on external registry**: Components pulled from shadcn's registry. Mitigation: once copied, you own the code — no dependency. But you don't get automatic upstream bug fixes.

### Ready for Proposal

Yes. The research is complete, technology choices are well-supported by current ecosystem data, and there are clear tradeoffs for each decision. The proposal phase can proceed with concrete structure and dependency lists.

### Decision Record

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Repo structure | Monorepo (backend/ + frontend/) | Single source of truth, atomic changes, simpler dev workflow |
| 2 | Dependency mgmt | uv | 10-100x faster than Poetry, built-in Python version mgmt, workspace support |
| 3 | ORM | SQLAlchemy 2.0 async | Maximum flexibility for future ML/analytics, mature ecosystem |
| 4 | Async DB driver | aiosqlite | Native SQLAlchemy support, async non-blocking I/O |
| 5 | Migrations | Alembic (async template) | Industry standard for SA, version-controlled schema changes |
| 6 | Frontend build | Vite 6+ | Fast, modern, CRA deprecated; Next.js is overkill for SPA |
| 7 | State management | Zustand + TanStack Query | Minimal boilerplate, excellent developer experience |
| 8 | UI library | shadcn/ui + Tailwind CSS 4 | Ownable components, no dependency lock-in, dashboard-native |
| 9 | Charts | Recharts | React-native, covers trading visualization needs |
| 10 | Python linting | ruff | Replaces flake8 + black + isort, extremely fast (Rust) |
| 11 | Testing (Python) | pytest + httpx + pytest-asyncio | Standard FastAPI testing stack |
| 12 | Testing (React) | vitest + @testing-library/react | Zero-config with Vite, DOM-based testing |
| 13 | CORS dev | Vite proxy | No CORS headers needed during development |
| 14 | Docker | No (MVP phase) | Adds unnecessary complexity for local-first app |
