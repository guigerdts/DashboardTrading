"""DI providers for the Edge Discovery module."""

from fastapi import Depends

from app.modules.edge_discovery.engine.edge_discovery_engine import EdgeDiscoveryEngine
from app.modules.edge_discovery.implementations.numpy_statistics_engine import NumpyStatisticsEngine
from app.modules.edge_discovery.implementations.sqlite_edge_repository import SqliteEdgeRepository
from app.modules.edge_discovery.interface.edge_repository import AbstractEdgeRepository
from app.modules.edge_discovery.interface.statistics_engine import AbstractStatisticsEngine


async def get_edge_repository() -> AbstractEdgeRepository:
    """Provide a request-scoped edge repository backed by SQLite."""
    return SqliteEdgeRepository()


async def get_statistics_engine() -> AbstractStatisticsEngine:
    """Provide a numpy-powered statistics engine."""
    return NumpyStatisticsEngine()


async def get_edge_discovery_service(
    repository: AbstractEdgeRepository = Depends(get_edge_repository),
    statistics_engine: AbstractStatisticsEngine = Depends(get_statistics_engine),
) -> EdgeDiscoveryEngine:
    """Provide a request-scoped EdgeDiscoveryEngine."""
    return EdgeDiscoveryEngine(
        repository=repository,
        statistics_engine=statistics_engine,
    )
