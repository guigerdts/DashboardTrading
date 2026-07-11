"""DI providers for the Edge Discovery module.

Extends the base dependencies with the service provider and
an admin auth guard for POST endpoints.
"""

from fastapi import BackgroundTasks, Depends, Header, HTTPException

from app.db.dependencies import get_uow
from app.db.unit_of_work import UnitOfWork
from app.modules.edge_discovery.engine.edge_discovery_engine import EdgeDiscoveryEngine
from app.modules.edge_discovery.implementations.numpy_statistics_engine import (
    NumpyStatisticsEngine,
)
from app.modules.edge_discovery.implementations.sqlite_edge_repository import (
    SqliteEdgeRepository,
)
from app.modules.edge_discovery.interface.edge_repository import AbstractEdgeRepository
from app.modules.edge_discovery.interface.statistics_engine import AbstractStatisticsEngine
from app.modules.edge_discovery.service import EdgeDiscoveryService


async def get_edge_repository() -> AbstractEdgeRepository:
    """Provide a request-scoped edge repository backed by SQLite."""
    return SqliteEdgeRepository()


async def get_statistics_engine() -> AbstractStatisticsEngine:
    """Provide a numpy-powered statistics engine."""
    return NumpyStatisticsEngine()


async def get_edge_discovery_engine(
    repository: AbstractEdgeRepository = Depends(get_edge_repository),
    statistics_engine: AbstractStatisticsEngine = Depends(get_statistics_engine),
) -> EdgeDiscoveryEngine:
    """Provide a request-scoped EdgeDiscoveryEngine."""
    return EdgeDiscoveryEngine(
        repository=repository,
        statistics_engine=statistics_engine,
    )


async def get_edge_discovery_service(
    background_tasks: BackgroundTasks,
    engine: EdgeDiscoveryEngine = Depends(get_edge_discovery_engine),
    repository: AbstractEdgeRepository = Depends(get_edge_repository),
    uow: UnitOfWork = Depends(get_uow),
) -> EdgeDiscoveryService:
    """Provide a request-scoped EdgeDiscoveryService."""
    return EdgeDiscoveryService(
        engine=engine,
        repository=repository,
        uow=uow,
        background_tasks=background_tasks,
    )


async def admin_required(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    """Temporary admin auth guard — checks for admin key header.

    Acts as a placeholder until a proper auth system is added.
    In development, any non-empty X-Admin-Key passes.
    In production, this would verify a JWT or session token.
    """
    if not x_admin_key:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )
