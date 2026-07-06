"""TIP domain models — all entities register on ``Base.metadata``."""

from app.models import catalogs  # noqa: F401  -- catalog lookups
from app.models.account import Account  # noqa: F401  -- trading account
from app.models.asset import Asset  # noqa: F401  -- tradeable instrument
from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.risk_profile import RiskProfile  # noqa: F401  -- risk presets
from app.models.strategy import Setup, Strategy, StrategySetup  # noqa: F401  -- strategy cluster
from app.models.trade import Trade  # noqa: F401  -- canonical trade entity

__all__ = [
    "Account",
    "Asset",
    "Base",
    "RiskProfile",
    "Setup",
    "SoftDeleteMixin",
    "Strategy",
    "StrategySetup",
    "TimestampMixin",
    "Trade",
]
