# Proposal: Base Architecture — Trade Intelligence Platform (TIP)

## Intent

Greenfield project with no codebase. This proposal creates the foundational monorepo structure with backend skeleton (FastAPI + SQLite) and frontend skeleton (React + Vite + Tailwind CSS, JavaScript only), enabling the team to start building domain modules immediately.

## Scope

### In Scope
- Monorepo layout: `backend/`, `frontend/`, root `Makefile`, root `README.md`
- Backend: FastAPI app factory, `GET /api/health`, 10 module skeletons with README + `__init__.py` + reserved routes, Alembic config, `pyproject.toml`
- Frontend: React + Vite (JS only, **no TypeScript**), Tailwind CSS, landing page with module navigation, 10 module directories with README + reserved route stubs
- Each module skeleton includes: `README.md` (purpose, scope, future plans), entry point, reserved routes, base structure
- Root tooling: `Makefile` with install, dev, lint, format, test, db-migrate commands
- Python toolchain: uv, ruff, pytest

### Out of Scope
- SQLAlchemy models, Pydantic schemas, services, repositories (deferred — Database First: design DB before any model code)
- Business endpoints (deferred to implementation phase after specs + design + tasks)
- Docker or containerization
- Authentication
- Broker or exchange integration
- AI/ML features

## Capabilities

### New Capabilities
- `dashboard`: Module skeleton — landing page with module navigation
- `trading-journal`: Module skeleton — reserved routes, README
- `analytics`: Module skeleton — reserved routes, README
- `risk-management`: Module skeleton — reserved routes, README
- `psychology`: Module skeleton — reserved routes, README
- `strategies`: Module skeleton — reserved routes, README
- `setups`: Module skeleton — reserved routes, README
- `screenshot-library`: Module skeleton — reserved routes, README
- `error-management`: Module skeleton — reserved routes, README
- `settings`: Module skeleton — reserved routes, README

### Modified Capabilities
None — greenfield project.

## Approach

Database First — no models, schemas, services, or repositories until DB design is finalized. This phase creates only the scaffolding: FastAPI app factory with health endpoint, Vite + React frontend with landing + navigation, and 10 module skeletons with README + reserved routes + entry points. Alembic configured for future migrations. Dev workflow unified via root Makefile. All architectural decisions documented in `openspec/` as the official source of truth.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/` | New | FastAPI app, health endpoint, 10 module stubs, Alembic config, pyproject.toml |
| `frontend/` | New | React + Vite app (JS), landing page, 10 module route stubs, Tailwind, package.json |
| `Makefile` | New | Unified dev commands |
| `README.md` | New | Project overview and setup guide |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| SQLite async concurrency | Low | WAL mode + single-writer connection pool |
| uv availability on target | Low | .python-version + pip fallback in Makefile |
| Tailwind without shadcn/ui (TS-first) | Low | Custom Tailwind components, JS-compatible |
| Module skeletons too generic | Low | Each has README with purpose, scope, future plans |

## Rollback Plan

All changes are additive — new files only. Rollback: `git clean -fd backend/ frontend/` + `git checkout Makefile README.md`. No data loss risk — no database exists.

## Dependencies

- Python 3.12+, Node.js 20+, npm
- uv (Python package manager)
- No external API keys or services

## Success Criteria

- [ ] `make install` installs all backend and frontend dependencies without errors
- [ ] `make dev` starts backend on `:8000` and frontend on `:5173`
- [ ] Vite proxy forwards `/api/*` to `http://localhost:8000`
- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] Frontend renders landing page with navigation links to all 10 modules
- [ ] Each backend module has `README.md`, `__init__.py`, and reserved route stub
- [ ] Each frontend module has README and reserved route in React Router
- [ ] `ruff check backend/` passes with zero errors
- [ ] No SQLAlchemy models, schemas, services, or repositories exist
- [ ] No business endpoints exist (only `GET /api/health`)
