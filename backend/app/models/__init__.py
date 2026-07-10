"""TIP domain models — all entities register on ``Base.metadata``."""

from app.models import catalogs  # noqa: F401  -- catalog lookups
from app.models.account import Account  # noqa: F401  -- trading account
from app.models.asset import Asset  # noqa: F401  -- tradeable instrument
from app.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.mistake import Mistake  # noqa: F401  -- mistake catalog
from app.models.psychology import (  # noqa: F401  -- psychology cluster
    Emotion,
    EmotionEntry,
    MistakeEntry,
    TradeTag,
)
from app.models.review import (  # noqa: F401  -- review cluster
    Attachment,
    Note,
    TradeReview,
)
from app.models.risk_profile import RiskProfile  # noqa: F401  -- risk presets
from app.models.strategy import Setup, Strategy, StrategySetup  # noqa: F401  -- strategy cluster
from app.models.tag import Tag  # noqa: F401  -- tag catalog
from app.models.trade import Trade  # noqa: F401  -- canonical trade entity
from app.models.trading_session import TradingSession  # noqa: F401  -- work sessions

__all__ = [
    "Account",
    "Asset",
    "Attachment",
    "Base",
    "Emotion",
    "EmotionEntry",
    "Mistake",
    "MistakeEntry",
    "Note",
    "RiskProfile",
    "Setup",
    "SoftDeleteMixin",
    "Strategy",
    "StrategySetup",
    "Tag",
    "TimestampMixin",
    "Trade",
    "TradeReview",
    "TradeTag",
    "TradingSession",
]
