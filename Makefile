.PHONY: install dev lint format test db-migrate

BACKEND_DIR = backend
FRONTEND_DIR = frontend

install:
	@command -v uv >/dev/null 2>&1 || { echo "Error: uv is not installed. See https://docs.astral.sh/uv/"; exit 1; }
	@command -v npm >/dev/null 2>&1 || { echo "Error: npm is not installed. See https://nodejs.org/"; exit 1; }
	cd $(BACKEND_DIR) && uv sync --dev
	cd $(FRONTEND_DIR) && npm install

dev:
	@echo "==> Starting backend on :8000..."
	cd $(BACKEND_DIR) && uv run uvicorn app.main:create_app --factory --reload --port 8000 &
	@sleep 2
	@echo "==> Starting frontend on :5173..."
	cd $(FRONTEND_DIR) && npm run dev

lint:
	cd $(BACKEND_DIR) && uv run ruff check .

format:
	cd $(BACKEND_DIR) && uv run ruff format .

test:
	cd $(BACKEND_DIR) && uv run pytest -v

db-migrate:
	cd $(BACKEND_DIR) && uv run alembic upgrade head
