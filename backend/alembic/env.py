"""Alembic environment configuration — sync engine, metadata from app.models.

Runs migrations using a sync SQLAlchemy engine against the TIP SQLite database.
The database URL is resolved from ``app.config.settings`` so it stays consistent
with the application configuration.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine

from alembic import context

# Ensure the project root (backend/) is on sys.path so app.* imports resolve.
_proj_root = str(Path(__file__).resolve().parent.parent)
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)

# ---------------------------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url from application settings so the same db_path
# is used by both the app and migrations.
from app.config import settings  # noqa: E402

config.set_main_option("sqlalchemy.url", f"sqlite:///{settings.db_path}")

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Target metadata — all models registered via ``app.models`` imports
# register their tables on ``Base.metadata`` automatically.
# ---------------------------------------------------------------------------
from app.models import Base  # noqa: E402

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Migration runners
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL as strings)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live database."""
    connectable = create_engine(config.get_main_option("sqlalchemy.url"))

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
