"""Asset domain model — a tradeable instrument within a market.

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Asset(Base, TimestampMixin, SoftDeleteMixin):
    """A tradeable asset linked to a market (e.g. EUR/USD → forex).

    References
    ----------
    - BR-16: ``(symbol, market_id)`` UNIQUE via ``uq_assets_symbol_market``
    """

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("markets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    symbol: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "symbol",
            "market_id",
            name="uq_assets_symbol_market",  # BR-16
        ),
    )
