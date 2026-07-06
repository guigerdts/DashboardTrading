"""Account domain model — a named financial account.

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""


import sqlalchemy as sa
from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Account(Base, TimestampMixin, SoftDeleteMixin):
    """A trading account (e.g. demo, live, paper) with status lifecycle.

    References
    ----------
    - BR-26: ``name`` UNIQUE
    - BR-27: ``status`` IN ('active', 'inactive')
    """

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        Text, nullable=False, unique=True  # BR-26
    )
    broker: Mapped[str | None] = mapped_column(Text, nullable=True)
    account_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_currency: Mapped[str] = mapped_column(
        Text, nullable=False, default="USD"
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="active"  # BR-27
    )

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('active', 'inactive')", name="ck_accounts_status"
        ),
    )
