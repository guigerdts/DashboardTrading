"""Pytest fixtures for all module tests.

Provides async infrastructure:
- ``event_loop`` (session-scoped): Required by pytest-asyncio for
  session-scoped async fixtures.
- ``async_engine`` (session-scoped): In-memory SQLite engine with all
  tables created once.
- ``db_session`` (per-test): Transaction-scoped session that rolls back
  after each test.
- ``client`` (per-test): FastAPI ``AsyncClient`` with overridden ``get_db``
  dependency (uses test in-memory DB).
- ``uow`` (per-test): ``UnitOfWork`` wrapping ``db_session`` — auto-rolls
  back after test.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.main import create_app
from app.models.base import Base

# ------------------------------------------------------------------
# Session-scoped event loop (required for session-scoped async fixtures)
# ------------------------------------------------------------------


@pytest.fixture(scope="session")
def event_loop() -> AsyncGenerator[asyncio.AbstractEventLoop, None]:
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ------------------------------------------------------------------
# Session-scoped in-memory engine
# ------------------------------------------------------------------


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Create an in-memory SQLite engine and all tables once per session."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


# ------------------------------------------------------------------
# Per-test transaction-scoped session
# ------------------------------------------------------------------


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a transaction-scoped session that rolls back after each test.

    Each test operates inside a transaction that is rolled back at teardown,
    ensuring complete isolation between tests.
    """
    connection = await async_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await transaction.rollback()
    await connection.close()


# ------------------------------------------------------------------
# Per-test FastAPI test client with overridden DB dependency
# ------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Provide a FastAPI test client with the in-memory test DB injected.

    Overrides ``app.db.dependencies.get_db`` so that all request handlers
    use the per-test ``db_session``.
    """
    from app.db.dependencies import get_db

    application = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    application.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ------------------------------------------------------------------
# Per-test UnitOfWork
# ------------------------------------------------------------------


@pytest_asyncio.fixture
async def uow(db_session):
    """Provide a ``UnitOfWork`` wrapping the per-test ``db_session``.

    Rolls back the session at teardown so no test data persists between runs.
    """
    from app.db.unit_of_work import UnitOfWork

    _uow = UnitOfWork(db_session)
    yield _uow
    await _uow.rollback()
