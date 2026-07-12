"""Strategy and Setup domain models — trading plans and entry/exit patterns.

Strategy and Setup have an M:N relationship via the ``strategy_setups``
junction table. Both are soft-deletable entities with unique names.

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Strategy(Base, TimestampMixin, SoftDeleteMixin):
    """A named trading strategy (e.g. Trend Following, Mean Reversion).

    References
    ----------
    - BR-14: ``name`` UNIQUE via ``uq_strategies_name``
    - BR-SL-06: ``active_version_id`` FK → strategy_versions.id (nullable)
    """

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,  # BR-14 — enforced by uq_strategies_name
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_version_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("strategy_versions.id"),
        nullable=True,
    )

    __table_args__ = (
        sa.UniqueConstraint("name", name="uq_strategies_name"),  # BR-14
    )


class Setup(Base, TimestampMixin, SoftDeleteMixin):
    """A named entry/exit pattern (e.g. Pin Bar, Engulfing, Breakout).

    References
    ----------
    - BR-15: ``name`` UNIQUE via ``uq_setups_name``
    """

    __tablename__ = "setups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,  # BR-15 — enforced by uq_setups_name
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("name", name="uq_setups_name"),  # BR-15
    )


class StrategySetup(Base):
    """M:N junction between Strategy and Setup.

    Both FKs cascade on delete — removing a strategy or setup cleans up
    its junction rows automatically.

    No audit or soft-delete columns — pure junction table per C4.
    """

    __tablename__ = "strategy_setups"

    strategy_id: Mapped[int] = mapped_column(
        ForeignKey("strategies.id", ondelete="CASCADE"), primary_key=True
    )
    setup_id: Mapped[int] = mapped_column(
        ForeignKey("setups.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (
        sa.Index("ix_strategy_setups_setup_id", "setup_id"),  # inverse lookup
    )
