# Tasks: Crear la arquitectura base de Trade Intelligence Platform

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,000–1,100 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Foundation → PR 2: Backend Modules → PR 3: Frontend Routes |
| Delivery strategy | force-chained |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Foundation (1.1–1.6) | PR 1 → main | Root structure, backend skeleton + config + tooling + health test, frontend skeleton |
| 2 | Backend Modules (1.7, 1.9) | PR 2 → main | All 10 module dirs + `__init__.py` + `router.py` + README, pluggable discovery wired in `create_app()` |
| 3 | Frontend Routes (1.8) | PR 3 → main | Landing page with module navigation, 10 route stubs in React Router |

## Phase 1: Infrastructure

- [x] **1.1 Monorepo** — Create root dirs (`backend/`, `frontend/`, `data/`, `docs/`, `assets/`), `.gitignore` (Python+Node+SQLite+user assets), `README.md` (TIP overview + setup). `assets/` subdirs: `screenshots/`, `icons/`, `logos/`, `themes/` (user data, not source code). Deps: none. Acceptance: `ls` shows all dirs, `.gitignore` hides `node_modules/`/`.venv`/`*.db`, `assets/` has 4 subdirs.
- [x] **1.2 Backend** — `backend/pyproject.toml` (fastapi, uvicorn, sqlalchemy, aiosqlite, alembic, pytest, httpx, ruff, pydantic-settings). Alembic skeleton: `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, empty `alembic/versions/`. Deps: 1.1. Acceptance: `uv sync` installs deps, `alembic` CLI available.
- [x] **1.3 Frontend** — `frontend/package.json` (react, react-dom, react-router-dom, vite, tailwindcss, postcss, autoprefixer), `vite.config.js` (proxy `/api/*` → `:8000`), `index.html`, `postcss.config.js`, `tailwind.config.js`, `src/main.jsx`, `src/index.css`, `src/api/client.js`, `src/lib/utils.js`. Deps: 1.1. Acceptance: `npm install` succeeds, Vite proxy forwards `/api/*`.
- [x] **1.4 Configuración** — `backend/app/config.py` (Pydantic Settings v2 with `TIP_` prefix, `db_path`, `debug`, `cors_origins`), `backend/app/database.py` (async engine + aiosqlite WAL + `get_async_session`), `backend/app/dependencies.py` (`get_db` async generator placeholder). Deps: 1.2. Acceptance: `Settings()` reads env, engine URL resolves, WAL mode enabled.
- [x] **1.5 Tooling** — Root `Makefile` (install, dev, lint, format, test, db-migrate targets using uv/npm/ruff/pytest). `[tool.ruff]` section in `pyproject.toml`. Deps: 1.2, 1.3. Acceptance: `make install` succeeds, `make format` formats code, `ruff check` passes.
- [x] **1.6 Health Check** — `backend/app/__init__.py`, `backend/app/main.py` (`create_app` factory + lifespan + CORS), `backend/app/api/__init__.py`, `backend/app/api/health.py` (GET `/api/health` → `{"status":"ok"}`), `backend/tests/__init__.py` + `tests/test_health.py` (httpx async test). Deps: 1.4, 1.5. Acceptance: `curl :8000/api/health` returns 200 with `{"status":"ok"}`, pytest passes.
- [x] **1.7 Módulos Backend** — 10 module dirs under `backend/app/modules/`: dashboard, trading_journal, analytics, risk_management, psychology, strategies, setups, screenshot_library, error_management, settings. Each with `__init__.py` (exports router), `router.py` (APIRouter + `raise NotImplementedError` stubs), `README.md` (purpose/scope/future). Deps: 1.1. Acceptance: 10 dirs × 3 files, `ruff check` passes, zero functional endpoints.
- [x] **1.8 Módulos Frontend** — `frontend/src/pages/Home.jsx` (landing with nav links to 10 TIP-official module names), `frontend/src/pages/ModuleTemplate.jsx` (generic placeholder), update `frontend/src/App.jsx` with 10 `<Route>` entries. Deps: 1.3. Acceptance: landing page renders 10 links, each navigates to placeholder with correct module name.
- [x] **1.9 Registro Pluggable** — `backend/app/modules/__init__.py` with `discover_modules()` using `importlib.import_module` to auto-register subdirectory routers. Wire into `create_app()` in `main.py`. Deps: 1.6, 1.7. Acceptance: adding a new module dir with `router.py` auto-registers without editing existing files.
