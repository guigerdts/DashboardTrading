"""Async SQLite database engine with WAL mode support.

Database First (C2): this module provides engine + session factory only.
No SQLAlchemy models, schemas, services, or repositories.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    f"sqlite+aiosqlite:///{settings.db_path}",
    echo=settings.db_echo,
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine.sync_engine, "connect")
def _set_foreign_keys(dbapi_connection, _connection_record) -> None:
    """Enable FK enforcement per SQLAlchemy sync connection.

    SQLite requires PRAGMA foreign_keys to be set per-connection.
    Listening on ``engine.sync_engine`` (the underlying sync engine of
    the AsyncEngine) ensures the pragma fires for every pooled connection.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session, ensuring clean close after use."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Enable WAL journal mode on startup.

    WAL mode provides better concurrent read/write performance for SQLite.
    Call this once during application lifespan.
    """
    async with engine.connect() as conn:
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
        await conn.commit()
