"""Tag domain model — free-form tags for trade annotation with category and color.

Tags are user-managed catalog entities (not seeded). They support categorization
via optional ``category`` and ``color`` fields for UI rendering, plus soft-delete
and audit timestamps.

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""

import sqlalchemy as sa
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Tag(Base, TimestampMixin, SoftDeleteMixin):
    """A free-form tag for trade annotation with optional category and color.

    Uniqueness is enforced via a unique constraint on ``name``.
    ``is_active`` enables archival without data loss.
    """

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("name", name="uq_tags_name"),
    )
