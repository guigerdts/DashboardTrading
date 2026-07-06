"""SQLAlchemy base model, mixins, and naming convention.

All domain models inherit from ``Base`` defined here.
Mixins provide common audit/soft-delete columns.
Uses SQLAlchemy 2.0 ``DeclarativeBase`` + ``Mapped`` style.
"""

from datetime import UTC, datetime

from sqlalchemy import Integer, MetaData, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> str:
    """ISO 8601 UTC timestamp string with millisecond precision and Z suffix.

    Example: ``2026-07-06T15:30:00.123Z``
    """
    now = datetime.now(UTC)
    return f"{now.strftime('%Y-%m-%dT%H:%M:%S')}.{now.microsecond // 1000:03d}Z"


convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)


class TimestampMixin:
    """Adds ``created_at`` (non-nullable, auto-set) and ``updated_at`` (nullable, auto-updated)."""

    created_at: Mapped[str] = mapped_column(Text, nullable=False, default=_utcnow)
    updated_at: Mapped[str | None] = mapped_column(Text, nullable=True, onupdate=_utcnow)


class SoftDeleteMixin:
    """Adds ``is_active`` (default 1) for logical deletion support."""

    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
