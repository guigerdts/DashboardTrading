"""SQLite connection factory for edge discovery cache.

Uses aiosqlite for async access. Database file is lazily created
at ``data/edge_cache.db`` relative to the project root.
"""

from __future__ import annotations

import os
from pathlib import Path

import aiosqlite

# Lazily resolved project root — set once via init_db()
_project_root: str | None = None


def _resolve_project_root() -> str:
    """Walk up from this file to find the project root (backend/)."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return str(parent)
    return str(current.parents[3])  # fallback: backend/


def get_db_path() -> str:
    """Return the path to the edge cache database file."""
    root = _resolve_project_root()
    data_dir = os.path.join(root, "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "edge_cache.db")


def _ddl() -> str:
    """Return DDL statements for the edge cache schema."""
    return """
    CREATE TABLE IF NOT EXISTS edge_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        trade_count INTEGER NOT NULL,
        group_count INTEGER NOT NULL,
        params TEXT NOT NULL,
        rankings TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS ix_edge_snapshots_created_at
        ON edge_snapshots(created_at DESC);
    """


async def get_connection() -> aiosqlite.Connection:
    """Create or retrieve an async SQLite connection.

    The database file is lazily created on first access.
    Schema is auto-created on first connection.
    """
    db_path = get_db_path()
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.executescript(_ddl())
    await conn.commit()
    return conn
