"""Psychology domain models — Emotion, Tag, Mistake catalogs and entry/junction tables.

Catalog tables (Emotion, Tag, Mistake) are simple lookups with ``(id, name, created_at)``.
Entry tables (EmotionEntry, MistakeEntry) link trades to catalog entries with per-instance
metadata. TradeTag is a pure M:N junction between Trade and Tag.

All catalog tables follow the same pattern as ``catalogs.py`` — ``Base`` only,
no ``TimestampMixin``, no ``SoftDeleteMixin`` (per C4).

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, _utcnow


class Emotion(Base):
    """Catalog of emotion types (e.g. calm, anxious, confident, fearful).

    Seeded catalog — read-only after seed. No ``updated_at`` per C4.

    References
    ----------
    - BR-18: ``name`` UNIQUE via ``uq_emotions_name``
    """

    __tablename__ = "emotions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)


class EmotionEntry(Base):
    """Per-trade emotional state recording with intensity and context phase.

    References
    ----------
    - BR-22: ``intensity`` BETWEEN 1 AND 10 via CHECK ``ck_emotion_entries_intensity``
    - BR-23: ``context`` IN ('before_entry', 'during_trade', 'after_exit') via CHECK
    - Design §6: FK to trades CASCADE, FK to emotions RESTRICT
    """

    __tablename__ = "emotion_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(
        ForeignKey("trades.id", ondelete="CASCADE"), nullable=False
    )
    emotion_id: Mapped[int] = mapped_column(
        ForeignKey("emotions.id", ondelete="RESTRICT"), nullable=False
    )
    intensity: Mapped[int] = mapped_column(Integer, nullable=False)  # BR-22
    context: Mapped[str] = mapped_column(Text, nullable=False)  # BR-23
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)

    __table_args__ = (
        sa.CheckConstraint(
            "intensity BETWEEN 1 AND 10", name="ck_emotion_entries_intensity"
        ),
        sa.CheckConstraint(
            "context IN ('before_entry', 'during_trade', 'after_exit')",
            name="ck_emotion_entries_context",
        ),
        sa.Index("ix_emotion_entries_emotion_id", "emotion_id"),
    )


class Tag(Base):
    """Catalog of free-form tags for trade annotation.

    References
    ----------
    - BR-19: ``name`` UNIQUE via ``uq_tags_name``
    - BR-21: non-empty trimmed (service-enforced)
    """

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)


class TradeTag(Base):
    """M:N junction between Trade and Tag.

    No audit or soft-delete columns — pure junction table per C4.
    Composite PK via (trade_id, tag_id).

    References
    ----------
    - Design §6: FK to trades CASCADE, FK to tags RESTRICT
    """

    __tablename__ = "trade_tags"

    trade_id: Mapped[int] = mapped_column(
        ForeignKey("trades.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.id", ondelete="RESTRICT"), primary_key=True
    )

    __table_args__ = (
        sa.Index("ix_trade_tags_tag_id", "tag_id"),
    )


class Mistake(Base):
    """Catalog of trading mistake types (e.g. fomo, revenge_trading, overtrading).

    Seeded catalog — read-only after seed. No ``updated_at`` per C4.

    References
    ----------
    - BR-20: ``name`` UNIQUE via ``uq_mistakes_name``
    """

    __tablename__ = "mistakes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)


class MistakeEntry(Base):
    """Per-trade mistake record linking a trade to a mistake catalog entry.

    References
    ----------
    - Design §6: FK to trades CASCADE, FK to mistakes RESTRICT
    """

    __tablename__ = "mistake_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(
        ForeignKey("trades.id", ondelete="CASCADE"), nullable=False
    )
    mistake_id: Mapped[int] = mapped_column(
        ForeignKey("mistakes.id", ondelete="RESTRICT"), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)

    __table_args__ = (
        sa.Index("ix_mistake_entries_mistake_id", "mistake_id"),
    )
