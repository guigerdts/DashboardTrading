"""Edge Discovery module — find statistical edges in closed trades.

v1.4.0: Backend core with engine, statistics, and SQLite storage.
"""

from __future__ import annotations

from app.modules.edge_discovery.engine import (
    Combinator,
    EdgeDiscoveryEngine,
    benjamini_hochberg,
    compute_edge_score,
    compute_stability_score,
    determine_confidence_level,
)
from app.modules.edge_discovery.implementations import (
    NumpyStatisticsEngine,
    SqliteEdgeRepository,
)
from app.modules.edge_discovery.interface import (
    AbstractEdgeRepository,
    AbstractStatisticsEngine,
)

__all__ = [
    "AbstractEdgeRepository",
    "AbstractStatisticsEngine",
    "Combinator",
    "EdgeDiscoveryEngine",
    "NumpyStatisticsEngine",
    "SqliteEdgeRepository",
    "benjamini_hochberg",
    "compute_edge_score",
    "compute_stability_score",
    "determine_confidence_level",
]
