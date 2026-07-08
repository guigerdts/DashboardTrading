"""add broker_ticket to trades

Revision ID: ebc4b9c1a9a0
Revises: e0843debd49b
Create Date: 2026-07-07 17:30:31.299122
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "ebc4b9c1a9a0"
down_revision: str | None = "e0843debd49b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trades", sa.Column("broker_ticket", sa.Text(), nullable=True))
    op.create_index(
        "ix_trades_account_broker_ticket",
        "trades",
        ["account_id", "broker_ticket"],
        unique=True,
        sqlite_where=sa.text("broker_ticket IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_trades_account_broker_ticket",
        table_name="trades",
        sqlite_where=sa.text("broker_ticket IS NOT NULL"),
    )
    op.drop_column("trades", "broker_ticket")
