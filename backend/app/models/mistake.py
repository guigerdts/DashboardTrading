"""Mistake domain model — catalog of trading mistake types with audit tracking.

Mistakes are user-managed catalog entities (not seeded) describing common
trading errors (e.g. fomo, revenge_trading, overtrading). They support
soft-delete and audit timestamps.

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""

import sqlalchemy as sa
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Mistake(Base, TimestampMixin, SoftDeleteMixin):
    """A type of trading mistake that can be linked to trades.

    Uniqueness is enforced via a unique constraint on ``name``.
    ``is_active`` enables archival without data loss.
    """

    __tablename__ = "mistakes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint("name", name="uq_mistakes_name"),
    )
