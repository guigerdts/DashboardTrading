"""Strategy Lab interfaces — abstract contracts for DI."""

from app.modules.strategy_lab.interfaces.comparison_engine import (
    ComparisonEngine,
    ComparisonResult,
)

__all__ = [
    "ComparisonEngine",
    "ComparisonResult",
]
