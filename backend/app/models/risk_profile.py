"""RiskProfile domain model — config-only risk management presets.

RiskProfile stores configuration values (max risk, sizing method, limits)
but NEVER computed metrics (PnL, R:R, Sharpe — those are always derived
on-the-fly per SSOT & C6 principles, Design §8).

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""

import sqlalchemy as sa
from sqlalchemy import REAL, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class RiskProfile(Base, TimestampMixin, SoftDeleteMixin):
    """Config-only risk preset for trade sizing and loss control.

    No CHECK constraints — all values are optional configuration knobs.
    No computed metrics are stored (Design §8).

    References
    ----------
    - Strategy FK with SET NULL — profile survives strategy deletion.
    """

    __tablename__ = "risk_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategies.id", ondelete="SET NULL"), nullable=True
    )
    max_risk_per_trade: Mapped[float | None] = mapped_column(REAL, nullable=True)
    position_sizing_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_daily_loss: Mapped[float | None] = mapped_column(REAL, nullable=True)
    max_concurrent_trades: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        sa.Index("ix_risk_profiles_strategy_id", "strategy_id"),  # FK index
    )
