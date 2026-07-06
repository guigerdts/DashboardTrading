# DashboardTrading — Trade Intelligence Platform (TIP)

Professional trading intelligence platform.
Stack: Python, FastAPI, React, SQLite.
Offline-first, modular, scalable.

## Architecture

```
DashboardTrading/
├── backend/     # FastAPI application (Python)
├── frontend/    # React SPA (JavaScript, Vite)
├── data/        # SQLite database (runtime)
├── assets/      # User assets (screenshots, icons, logos, themes)
├── docs/        # Project documentation
└── openspec/    # SDD specifications and planning
```

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
| `make lint` | Lint backend code (ruff) |
| `make format` | Format backend code (ruff) |
| `make test` | Run backend tests (pytest) |
| `make db-migrate` | Run pending Alembic migrations |

## Status

Greenfield — scaffolding in progress.
