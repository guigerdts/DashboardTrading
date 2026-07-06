# Base Architecture Specification

## Purpose

This specification defines the foundational monorepo scaffolding for the Trade Intelligence Platform (TIP). It covers the root structure, FastAPI backend skeleton, React frontend skeleton, database readiness configuration, developer tooling, and cross-cutting architectural constraints. No business logic, domain models, or API endpoints beyond `GET /api/health` are included.

## Architectural Constraints

These rules apply to ALL requirements below and MUST NOT be violated by any implementation.

| ID | Constraint | Rule |
|----|-----------|------|
| C1 | **Modularity** | Each module MUST be fully decoupled. Cross-module direct dependencies are PROHIBITED. Communication between modules MUST use defined interfaces or services only. |
| C2 | **Database First** | Domain entities, tables, SQLAlchemy models, repositories, business services, and functional endpoints MUST NOT be created until the DB design and functional spec are complete. This scaffolding phase creates infrastructure only. |
| C3 | **Frontend scope** | Modules MUST expose only their base structure (README, route, entry point). No business logic or module-specific UI components. |
| C4 | **Backend scope** | In addition to `GET /api/health`, each module MUST define a router file with structure for future endpoints — but MUST NOT implement any functional endpoint logic. |
| C5 | **Naming conventions** | All folders, files, and module names MUST use consistent terminology aligned with the official TIP project glossary. |
| C6 | **Scalability** | The architecture MUST support adding new modules without modifying existing ones — pluggable registration pattern. |

## Requirements

### Requirement: Root Monorepo Structure

The project root MUST contain a `backend/` directory, a `frontend/` directory, a `Makefile`, and a `README.md`.

#### Scenario: Root directory layout

- GIVEN the project root
- WHEN listing the top-level contents
- THEN `backend/`, `frontend/`, `Makefile`, and `README.md` MUST all exist

#### Scenario: Makefile targets

- GIVEN the root `Makefile`
- WHEN listing targets
- THEN `install`, `dev`, `lint`, `format`, `test`, and `db-migrate` MUST all be defined

#### Scenario: Missing dependency handling

- GIVEN `make install` is run
- WHEN `uv` or `npm` is not installed
- THEN the command MUST fail with a clear error message before attempting installation

### Requirement: Backend Scaffolding

The backend MUST provide a FastAPI application factory, a health-check endpoint, and skeleton modules for all 10 domains. Each module MUST define a router file with structural stubs but no functional endpoint logic (C3, C4).

#### Scenario: Health endpoint

- GIVEN the backend is running
- WHEN a GET request is sent to `/api/health`
- THEN the response MUST be 200 with body `{"status": "ok"}`

#### Scenario: All 10 module directories exist

- GIVEN the `backend/` directory
- WHEN listing subdirectories
- THEN the following MUST all exist: `dashboard`, `trading_journal`, `analytics`, `risk_management`, `psychology`, `strategies`, `setups`, `screenshot_library`, `error_management`, `settings`

#### Scenario: Module skeleton contents

- GIVEN each backend module directory
- THEN it MUST contain a `README.md` (purpose, scope, future plans), an `__init__.py`, and a `router.py` with structural endpoint stubs
- AND each module MUST be registered in the app factory without importing other modules directly (C1)

#### Scenario: No functional endpoints

- GIVEN all backend module router files
- WHEN searching for HTTP method decorators (`@router.get`, `@router.post`, etc.) beyond the health endpoint
- THEN zero functional endpoint definitions MUST be found — only `pass`, `raise NotImplementedError`, or similar stubs

#### Scenario: Linter compliance

- GIVEN the backend code
- WHEN running `ruff check backend/`
- THEN zero errors MUST be reported

### Requirement: Frontend Scaffolding

The frontend MUST provide a Vite + React dev server (JavaScript only, no TypeScript), a landing page with navigation, and route stubs for all 10 modules. Module directories MUST contain only base structure — no business components or logic (C3).

#### Scenario: Dev server starts

- GIVEN frontend dependencies are installed
- WHEN the dev server is started
- THEN it MUST listen on port `:5173`

#### Scenario: Vite proxy

- GIVEN the frontend dev server is running
- WHEN a request is sent to `/api/*`
- THEN the Vite proxy MUST forward it to `http://localhost:8000`

#### Scenario: Landing page with module navigation

- GIVEN the frontend is served
- WHEN the root page is loaded
- THEN it MUST render navigation links to all 10 modules using TIP-official names: Dashboard, Trading Journal, Analytics, Risk Management, Psychology, Strategies, Setups, Screenshot Library, Error Management, Settings (C5)

#### Scenario: Module route stubs

- GIVEN the frontend router configuration
- THEN each of the 10 modules MUST have a reserved route in React Router
- AND each module MUST be importable without hard dependencies on other modules (C1, C6)

#### Scenario: No business components

- GIVEN all frontend module directories
- WHEN scanning for component files outside the route stub
- THEN only landing/navigation infrastructure MAY exist — no module-specific business components

### Requirement: Database Readiness

The backend MUST be configured for SQLite with Alembic but MUST NOT contain any domain entities, tables, SQLAlchemy models, repositories, business services, or functional endpoints (C2).

#### Scenario: SQLite and Alembic configured

- GIVEN the backend `pyproject.toml`
- THEN `aiosqlite`, `sqlalchemy`, `alembic` MUST be declared as dependencies
- AND Alembic MUST be initialized (migrations directory exists)
- AND no migration revision files MUST exist

#### Scenario: No domain models exist

- GIVEN the entire `backend/` directory
- WHEN searching for SQLAlchemy model definitions (`Column`, `Table`, `declarative_base`, `Mapped`, `mapped_column`)
- THEN zero matches MUST be found

#### Scenario: No business services or repositories

- GIVEN the entire `backend/` directory
- WHEN searching for service or repository class definitions
- THEN zero matches MUST be found outside documentation or README references

### Requirement: Tooling Integrity

All developer tooling MUST produce consistent, passing results on the scaffolded code.

#### Scenario: Port conflict — backend

- GIVEN port 8000 is already in use
- WHEN the backend dev server starts
- THEN it MUST fail with a clear port-in-use error and non-zero exit code

#### Scenario: Port conflict — frontend

- GIVEN port 5173 is already in use
- WHEN the frontend dev server starts
- THEN it MUST fail with a clear port-in-use error and non-zero exit code

#### Scenario: Install workflow

- GIVEN a clean checkout
- WHEN running `make install`
- THEN all backend (Python via uv) and frontend (JavaScript via npm) dependencies MUST be installed without errors

#### Scenario: Module structure verification

- GIVEN the full project
- WHEN verifying module structure
- THEN exactly 10 backend modules with `__init__.py` + `README.md` + `router.py` and exactly 10 frontend modules with `README.md` + route stub MUST be present
- AND all module names MUST conform to the TIP official naming convention (C5)
