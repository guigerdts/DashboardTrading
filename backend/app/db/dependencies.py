"""FastAPI dependency injection container for the application layer.

Provides:
- ``get_db``: Yields an ``AsyncSession`` per request.
- ``get_uow``: Yields a ``UnitOfWork``; commits on success, rolls back on error.
- Service providers: ``get_trade_service``, ``get_account_service``,
  ``get_asset_service``, ``get_broker_service`` — each wraps the UoW
  dependency.

QC-03: Provider bodies contain exactly ``from ... import Service; return Service(uow)``
with string return-type annotations. Zero business logic.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory

# ------------------------------------------------------------------
# Session & Unit of Work
# ------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    The session is closed in the ``finally`` block after the request completes.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_uow(
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator["UnitOfWork", None]:  # type: ignore[empty-body]  # noqa: F821
    """FastAPI dependency that yields a ``UnitOfWork``.

    Commits on success, rolls back and re-raises on exception.
    """
    from app.db.unit_of_work import UnitOfWork

    uow = UnitOfWork(db)
    try:
        yield uow
        await uow.commit()
    except Exception:
        await uow.rollback()
        raise


# ------------------------------------------------------------------
# Service providers (late imports — modules may not exist yet)
# QC-03: Each provider body is exactly: from ... import Service; return Service(uow)
# ------------------------------------------------------------------


async def get_trade_service(
    uow=Depends(get_uow),
) -> "TradeService":  # type: ignore[empty-body]  # noqa: F821
    """Provide a ``TradeService`` instance for the current request."""
    from app.modules.trades.service import TradeService

    return TradeService(uow)


async def get_account_service(
    uow=Depends(get_uow),
) -> "AccountService":  # type: ignore[empty-body]  # noqa: F821
    """Provide an ``AccountService`` instance for the current request."""
    from app.modules.accounts.service import AccountService

    return AccountService(uow)


async def get_asset_service(
    uow=Depends(get_uow),
) -> "AssetService":  # type: ignore[empty-body]  # noqa: F821
    """Provide an ``AssetService`` instance for the current request."""
    from app.modules.assets.service import AssetService

    return AssetService(uow)


async def get_broker_service(
    uow=Depends(get_uow),
) -> "BrokerService":  # type: ignore[empty-body]  # noqa: F821
    """Provide a ``BrokerService`` instance for the current request."""
    from app.modules.catalogs.service import BrokerService

    return BrokerService(uow)
