"""Catalog lookup tables — Market, MarketSession, Timeframe, Broker.

All catalog tables are simple lookups with ``(id, name)`` and optional
audit columns. No seed data is included here — only table structure.
Seed data belongs in a dedicated Alembic migration (PR 5).
Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""

from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, _utcnow


class Market(Base):
    """Asset-class / market lookup (e.g. forex, crypto, equities).

    Seeded catalog — read-only after seed. No ``updated_at`` per C4.
    """

    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)


class MarketSession(Base):
    """Trading-session lookup (e.g. asian, european, american).

    Seeded catalog — read-only after seed. No ``updated_at`` per C4.
    """

    __tablename__ = "market_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)


class Timeframe(Base):
    """Chart timeframe lookup (e.g. M1, M5, M15, H1, H4, D1, W1).

    Seeded catalog — read-only after seed. No ``updated_at`` per C4.
    """

    __tablename__ = "timeframes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)


class Broker(Base, TimestampMixin, SoftDeleteMixin):
    """Trading-broker catalog.

    User-defined (not seeded). Name is NOT unique at DB level
    (BR-17 — uniqueness is a service-level suggestion only).
    """

    __tablename__ = "brokers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
