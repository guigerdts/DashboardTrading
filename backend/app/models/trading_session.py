"""TradingSession domain model — user-defined work sessions grouping trades.

A TradingSession groups multiple trades into a named work session with
a start/end datetime range and optional notes.

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class TradingSession(Base, TimestampMixin, SoftDeleteMixin):
    """A named work session spanning multiple trades.

    References
    ----------
    - BR-28: ``start_datetime`` <= ``end_datetime`` (service-enforced)
    - Design §6: FK to trades uses SET NULL — session deleted, trades remain.
    """

    __tablename__ = "trading_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    start_datetime: Mapped[str] = mapped_column(Text, nullable=False)
    end_datetime: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
