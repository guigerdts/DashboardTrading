"""seed psychology tables — emotions, mistakes

Revision ID: e0843debd49b
Revises: 95da0ec91fc5
Create Date: 2026-07-06 19:15:30.000000
"""
from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e0843debd49b'
down_revision: str | None = '95da0ec91fc5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _utcnow() -> str:
    """ISO 8601 UTC timestamp string with millisecond precision and Z suffix."""
    now = datetime.now(UTC)
    return f"{now.strftime('%Y-%m-%dT%H:%M:%S')}.{now.microsecond // 1000:03d}Z"


def _seed_table(table_name: str, names: list[str]) -> None:
    """Insert rows by name using INSERT OR IGNORE for idempotent seed.

    Catalog tables have ``created_at`` NOT NULL with no server default,
    so the timestamp must be provided explicitly.
    """
    conn = op.get_bind()
    table = sa.table(table_name, sa.column('name', sa.Text), sa.column('created_at', sa.Text))
    for name in names:
        conn.execute(
            table.insert().prefix_with('OR IGNORE').values(name=name, created_at=_utcnow())
        )


def upgrade() -> None:
    _seed_table('emotions', [
        'calm', 'anxious', 'confident', 'fearful', 'greedy',
        'neutral', 'excited', 'frustrated', 'disappointed',
        'apathetic', 'hopeful', 'regretful',
    ])
    _seed_table('mistakes', [
        'fomo', 'revenge_trading', 'overtrading', 'no_stop_loss',
        'moving_stop_loss', 'holding_losers', 'cutting_winners',
        'ignoring_risk', 'bad_entry', 'no_plan', 'emotional_trading',
    ])


def downgrade() -> None:
    conn = op.get_bind()
    for name in ['calm', 'anxious', 'confident', 'fearful', 'greedy',
                  'neutral', 'excited', 'frustrated', 'disappointed',
                  'apathetic', 'hopeful', 'regretful']:
        conn.execute(sa.text("DELETE FROM emotions WHERE name = :n"), {"n": name})
    for name in ['fomo', 'revenge_trading', 'overtrading', 'no_stop_loss',
                  'moving_stop_loss', 'holding_losers', 'cutting_winners',
                  'ignoring_risk', 'bad_entry', 'no_plan', 'emotional_trading']:
        conn.execute(sa.text("DELETE FROM mistakes WHERE name = :n"), {"n": name})
