"""Trade domain model — the canonical trading entity.

Trade is the single source of truth for all trading data.
Derived metrics (PnL, R:R) are computed on-the-fly per SSOT & C6 principles.

Uses SQLAlchemy 2.0 ``Mapped`` + ``mapped_column`` style.
"""


import sqlalchemy as sa
from sqlalchemy import REAL, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class Trade(Base, TimestampMixin, SoftDeleteMixin):
    """A single trade entry — canonical entity for all trading data.

    Wide table with 9 FKs radiating to lookup, entity, and catalog tables.
    All CHECK-enforced invariants mirror domain rules (BR-01 through BR-29).

    References
    ----------
    - BR-01: ``asset_id`` NOT NULL + FK RESTRICT
    - BR-02: ``direction`` IN ('long', 'short')
    - BR-03: ``quantity`` > 0
    - BR-04: ``entry_price`` > 0
    - BR-05: ``entry_datetime`` NOT NULL
    - BR-06: ``account_id`` NOT NULL + FK RESTRICT
    - BR-10: exit_price / exit_datetime both NULL or both set (service-enforced)
    - BR-11: ``status`` IN ('open', 'closed')
    - BR-12: ``editable_until`` 30d post-close (service-enforced)
    - BR-13: ``position_size`` >= 0
    - BR-25: ``commission`` DEFAULT 0
    """

    __tablename__ = "trades"

    # ------------------------------------------------------------------
    # Surrogate key
    # ------------------------------------------------------------------
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ------------------------------------------------------------------
    # Required FKs (RESTRICT on delete — never orphan trades)
    # ------------------------------------------------------------------
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="RESTRICT"),  # BR-06
        nullable=False,
    )
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="RESTRICT"),  # BR-01
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Direction & status (CHECK-enforced enums)
    # ------------------------------------------------------------------
    direction: Mapped[str] = mapped_column(
        Text, nullable=False  # BR-02 — CHECK in __table_args__
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="open"  # BR-11 — CHECK in __table_args__
    )

    # ------------------------------------------------------------------
    # Core required numeric fields
    # ------------------------------------------------------------------
    entry_price: Mapped[float] = mapped_column(
        REAL, nullable=False  # BR-04 — CHECK in __table_args__
    )
    quantity: Mapped[float] = mapped_column(
        REAL, nullable=False  # BR-03 — CHECK in __table_args__
    )
    entry_datetime: Mapped[str] = mapped_column(
        Text, nullable=False  # BR-05
    )

    # ------------------------------------------------------------------
    # Optional FKs (SET NULL on delete — trade survives parent deletion)
    # ------------------------------------------------------------------
    # Tables created in PR 1 (catalogs)
    broker_id: Mapped[int | None] = mapped_column(
        ForeignKey("brokers.id", ondelete="SET NULL"), nullable=True
    )
    market_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("market_sessions.id", ondelete="SET NULL"), nullable=True
    )
    timeframe_id: Mapped[int | None] = mapped_column(
        ForeignKey("timeframes.id", ondelete="SET NULL"), nullable=True
    )
    # NOTE: FKs to future tables (PR 3 / PR 4).
    # SQLAlchemy ForeignKey is omitted here because the referenced tables
    # (strategies, setups, risk_profiles, trading_sessions) don't exist yet.
    # The FK constraints ARE added inline in the hand-edited migration so they
    # exist at CREATE TABLE time — required because SQLite cannot ALTER TABLE
    # ADD CONSTRAINT later. The ORM-level FK metadata gap is acceptable since
    # relationships are not defined in this phase.
    strategy_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    setup_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    risk_profile_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    trading_session_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )

    # ------------------------------------------------------------------
    # Exit fields (both NULL or both set — service-level BR-10)
    # ------------------------------------------------------------------
    exit_price: Mapped[float | None] = mapped_column(REAL, nullable=True)
    exit_datetime: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Risk management
    # ------------------------------------------------------------------
    stop_loss: Mapped[float | None] = mapped_column(REAL, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(REAL, nullable=True)
    position_size: Mapped[float | None] = mapped_column(
        REAL, nullable=True  # BR-13 — CHECK in __table_args__
    )

    # ------------------------------------------------------------------
    # Fees
    # ------------------------------------------------------------------
    commission: Mapped[float] = mapped_column(
        REAL, nullable=False, default=0  # BR-25 — CHECK in __table_args__
    )
    swap_fees: Mapped[float] = mapped_column(
        REAL, nullable=False, default=0  # CHECK in __table_args__
    )

    # ------------------------------------------------------------------
    # Risk amount (user-entered, not computed)
    # ------------------------------------------------------------------
    risk_amount: Mapped[float | None] = mapped_column(REAL, nullable=True)

    # NOTE: pnl, pnl_points, and r_multiple are NOT stored — they are
    # computed on-the-fly per SSOT & C6 principles (see Design §1).

    # ------------------------------------------------------------------
    # Audit / soft-lock
    # ------------------------------------------------------------------
    editable_until: Mapped[str | None] = mapped_column(
        Text, nullable=True  # BR-12 — service-enforced
    )
    notes_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ------------------------------------------------------------------
    # Constraints & indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # ---- CHECK constraints ----
        sa.CheckConstraint("direction IN ('long', 'short')", name="ck_trades_direction"),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_trades_status"),
        sa.CheckConstraint("entry_price > 0", name="ck_trades_entry_price"),
        sa.CheckConstraint("quantity > 0", name="ck_trades_quantity"),
        sa.CheckConstraint("position_size >= 0", name="ck_trades_position_size"),
        sa.CheckConstraint("commission >= 0", name="ck_trades_commission"),
        sa.CheckConstraint("swap_fees >= 0", name="ck_trades_swap_fees"),
        # ---- FK indexes (9) ----
        sa.Index("ix_trades_account_id", "account_id"),
        sa.Index("ix_trades_asset_id", "asset_id"),
        sa.Index("ix_trades_broker_id", "broker_id"),
        sa.Index("ix_trades_market_session_id", "market_session_id"),
        sa.Index("ix_trades_timeframe_id", "timeframe_id"),
        sa.Index("ix_trades_strategy_id", "strategy_id"),
        sa.Index("ix_trades_setup_id", "setup_id"),
        sa.Index("ix_trades_risk_profile_id", "risk_profile_id"),
        sa.Index("ix_trades_trading_session_id", "trading_session_id"),
        # ---- Date range indexes (2) ----
        sa.Index("ix_trades_entry_datetime", "entry_datetime"),
        sa.Index("ix_trades_exit_datetime", "exit_datetime"),
        # ---- Direction filter ----
        sa.Index("ix_trades_direction", "direction"),
        # ---- Composite indexes (3) ----
        sa.Index(
            "ix_trades_status_entry_datetime", "status", "entry_datetime"
        ),
        sa.Index(
            "ix_trades_asset_entry_datetime", "asset_id", "entry_datetime"
        ),
        sa.Index(
            "ix_trades_strategy_entry_datetime", "strategy_id", "entry_datetime"
        ),
    )
