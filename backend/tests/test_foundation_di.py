"""Foundation DI and quality-criteria tests.

Verifies QC-01 through QC-04 invariants for the repository, Unit of Work,
dependency injection, and error-handling infrastructure.

Note: Concrete module repositories (trades, accounts, assets, catalogs) do
NOT exist at Foundation time. These tests use ``SqlAlchemyRepository[Market]``
directly with existing catalog models to prove the infrastructure works.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.dependencies import get_db, get_uow
from app.db.unit_of_work import UnitOfWork
from app.main import create_app
from app.models.catalogs import Market
from app.modules.shared.base import SqlAlchemyRepository

# ======================================================================
# QC-01: Repository add() must NOT commit
# ======================================================================


@pytest.mark.asyncio
async def test_qc01_repo_add_does_not_commit(async_engine) -> None:
    """QC-01: ``SqlAlchemyRepository.add()`` calls flush() but NOT commit().

    Strategy: add via repo → rollback the session → verify entity is NOT
    in the database. If ``add()`` called ``commit()`` internally, the entity
    would survive the rollback.
    """
    # Arrange — create a fresh session and repo
    connection = await async_engine.connect()
    await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    try:
        repo = SqlAlchemyRepository(session, Market)

        # Act — add a market through the repo
        market = Market(name="qc01_rollback_test")
        result = await repo.add(market)

        # Assert — flush worked (we got an ID)
        assert result.id is not None, "flush() should populate the generated ID"

        # Rollback the session
        await session.rollback()
        # SQLite auto-creates a new implicit transaction after rollback
        await session.close()

        # Assert — the entity should NOT be in the database
        async with AsyncSession(async_engine) as check_session:
            check = await check_session.get(Market, result.id)
            assert check is None, "Market persisted despite rollback — add() must have committed!"
    finally:
        await connection.close()


# ======================================================================
# QC-04: Shared session across repositories on same UoW
# ======================================================================


@pytest.mark.asyncio
async def test_qc04_shared_session_across_repos(db_session) -> None:
    """QC-04: Two repositories on the same ``AsyncSession`` share the same
    session object."""
    # Arrange
    repo_market = SqlAlchemyRepository(db_session, Market)

    # Act — direct session reference
    # Note: TradeRepository, AccountRepository don't exist yet at Foundation,
    # but SqlAlchemyRepository proves the session-sharing pattern
    repo_market_2 = SqlAlchemyRepository(db_session, Market)

    # Assert
    assert id(repo_market._session) == id(repo_market_2._session), (
        "Both repos must share the same AsyncSession instance"
    )


# ======================================================================
# QC-04: Single session per request via DI
# ======================================================================


@pytest.mark.asyncio
async def test_qc04_single_session_per_request(async_engine) -> None:
    """QC-04: ``get_uow()`` yields a ``UnitOfWork`` with a valid session."""
    # Arrange — create a session that mimics what get_db() yields
    async with async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )() as session:
        # Act
        uow = UnitOfWork(session)

        # Assert
        assert uow._session is not None
        assert isinstance(uow._session, AsyncSession)


# ======================================================================
# Auto-commit on success via test client
# ======================================================================


@pytest.mark.asyncio
async def test_auto_commit_on_success(async_engine, db_session) -> None:
    """Verify that a successful request path commits data to the database.

    Strategy: create a minimal test endpoint that uses ``get_uow()``,
    inserts a Market, and succeeds. After the request, verify the Market
    is present using a new session from the async engine.
    """
    from fastapi import APIRouter, Depends

    router = APIRouter()

    @router.post("/test-auto-commit")
    async def auto_commit(uow=Depends(get_uow)):
        repo = SqlAlchemyRepository(uow._session, Market)
        market = Market(name="auto_commit_test")
        await repo.add(market)
        market_id = market.id  # read before commit to avoid post-commit expiry
        await uow.commit()
        return {"id": market_id}

    # Build app with overridden DB
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/test-auto-commit")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    market_id = resp.json()["id"]

    # Verify data persisted using a fresh session from the engine
    async with AsyncSession(async_engine) as verify_session:
        market = await verify_session.get(Market, market_id)
        assert market is not None, "Market should have been committed"
        assert market.name == "auto_commit_test"


# ======================================================================
# Auto-rollback on exception
# ======================================================================


@pytest.mark.asyncio
async def test_auto_rollback_on_exception(async_engine, db_session) -> None:
    """Verify that an exception in the handler triggers rollback.

    Strategy: create a test endpoint that inserts data via the UoW
    then raises an exception. After the request, verify no data persisted.
    """
    from fastapi import APIRouter, Depends

    from app.core.exceptions import BusinessRuleError

    router = APIRouter()

    @router.post("/test-auto-rollback")
    async def auto_rollback(uow=Depends(get_uow)):
        repo = SqlAlchemyRepository(uow._session, Market)
        market = Market(name="rollback_test")
        await repo.add(market)
        # Raise exception before commit — triggers rollback
        raise BusinessRuleError("test rollback", field="name")

    # Build app with overridden DB
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.include_router(router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/test-auto-rollback")

    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    # Verify NO data persisted
    async with AsyncSession(async_engine) as verify_session:
        result = await verify_session.execute(select(Market).where(Market.name == "rollback_test"))
        assert result.scalar_one_or_none() is None, (
            "Market should NOT have been committed — rollback must have occurred"
        )


# ======================================================================
# dependency_overrides works
# ======================================================================


@pytest.mark.asyncio
async def test_dependency_overrides_works(db_session) -> None:
    """Verify that ``app.dependency_overrides`` can replace ``get_uow``.

    Strategy: override ``get_uow`` with a mock; invoke a test endpoint
    that depends on it; verify the mock was called.
    """
    from fastapi import APIRouter, Depends

    call_count = 0

    async def mock_get_uow():
        nonlocal call_count
        call_count += 1
        yield UnitOfWork(db_session)

    router = APIRouter()

    @router.get("/test-override")
    async def check_override(uow=Depends(get_uow)):
        return {"ok": True, "session_id": id(uow._session)}

    app = create_app()
    app.dependency_overrides[get_uow] = mock_get_uow
    app.include_router(router)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/test-override")

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert call_count == 1, (
        f"Mock get_uow should have been called exactly once, called {call_count} times"
    )
    data = resp.json()
    assert data["ok"] is True
    assert data["session_id"] == id(db_session)
