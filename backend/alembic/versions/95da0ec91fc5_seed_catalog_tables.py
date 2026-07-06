"""seed catalog tables — markets, market_sessions, timeframes

Revision ID: 95da0ec91fc5
Revises: 93fa025b4e22
Create Date: 2026-07-06 19:15:00.000000
"""
from datetime import UTC, datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95da0ec91fc5'
down_revision: Union[str, None] = '93fa025b4e22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    _seed_table('markets', [
        'forex', 'indices', 'commodities', 'crypto',
        'equities', 'bonds', 'etfs',
    ])
    _seed_table('market_sessions', [
        'asian', 'european', 'american',
        'asian_european_overlap', 'european_american_overlap',
        'weekend', 'opening_auction',
    ])
    _seed_table('timeframes', [
        'M1', 'M5', 'M15', 'M30',
        'H1', 'H2', 'H4',
        'D1', 'W1', 'MN',
    ])


def downgrade() -> None:
    conn = op.get_bind()
    for name in ['forex', 'indices', 'commodities', 'crypto', 'equities', 'bonds', 'etfs']:
        conn.execute(sa.text("DELETE FROM markets WHERE name = :n"), {"n": name})
    for name in ['asian', 'european', 'american', 'asian_european_overlap',
                  'european_american_overlap', 'weekend', 'opening_auction']:
        conn.execute(sa.text("DELETE FROM market_sessions WHERE name = :n"), {"n": name})
    for name in ['M1', 'M5', 'M15', 'M30', 'H1', 'H2', 'H4', 'D1', 'W1', 'MN']:
        conn.execute(sa.text("DELETE FROM timeframes WHERE name = :n"), {"n": name})
