"""Review domain models — Note, TradeReview, Attachment.

Note and TradeReview are text-anchored review entities attached to a Trade.
Attachment is a type-discriminated file reference with soft-delete support.

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.

Deviations from Design
----------------------
- TradeReview: ``rating_grade`` column REMOVED per user request.
  Only text (``content``) and ``lesson_learned`` — no rating/categories.
- Attachment type CHECK: limited to IN ('image') for MVP per user request.
  Will expand when more types are added. Design had ('image', 'pdf', 'document', 'video', 'other').
"""

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, _utcnow


class Note(Base, TimestampMixin):
    """A free-form text note attached to a trade.

    No ``SoftDeleteMixin`` — notes have no ``is_active`` per Design §4.
    FK to trades cascades on delete.

    References
    ----------
    - Design §6: FK to trades CASCADE
    """

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(
        ForeignKey("trades.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)


class TradeReview(Base, TimestampMixin):
    """A structured review of a trade with text analysis and lessons learned.

    .. caution::
       ``rating_grade`` is intentionally omitted per user request.
       This table stores only free-text reflection — no ratings or categories.

    No ``SoftDeleteMixin`` — reviews have no ``is_active`` per Design §4.
    FK to trades cascades on delete.
    """

    __tablename__ = "trade_reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(
        ForeignKey("trades.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    lesson_learned: Mapped[str | None] = mapped_column(Text, nullable=True)


class Attachment(Base, SoftDeleteMixin):
    """A type-discriminated file reference attached to a trade.

    .. caution::
       For MVP, the ``type`` CHECK constraint only allows ``'image'``.
       When more types are needed, update the CHECK to include
       ``'pdf'``, ``'document'``, ``'video'``, ``'other'``.

    Has ``created_at`` but NOT ``updated_at`` — timestamps are immutable
    after creation. ``is_active`` is inherited from ``SoftDeleteMixin``.
    FK to trades cascades on delete.

    References
    ----------
    - BR-24: file_size_bytes <= 10MB (service-enforced at upload)
    """

    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(
        ForeignKey("trades.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)

    __table_args__ = (
        sa.CheckConstraint("type IN ('image')", name="ck_attachments_type"),
    )
