"""Edge Discovery interfaces — abstract contracts for DI."""

from app.modules.edge_discovery.interface.edge_repository import AbstractEdgeRepository
from app.modules.edge_discovery.interface.statistics_engine import AbstractStatisticsEngine

__all__ = [
    "AbstractEdgeRepository",
    "AbstractStatisticsEngine",
]
