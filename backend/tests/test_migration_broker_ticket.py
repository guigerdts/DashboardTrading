"""Migration tests for ``ebc4b9c1a9a0_add_broker_ticket_to_trades.py``.

Verifies:
- broker_ticket column exists and is nullable TEXT
- Multiple NULL broker_tickets allowed
- Unique per account (same account + same ticket = IntegrityError)
- Same ticket for different accounts allowed

Uses raw SQL queries against the test DB's existing schema.
The migration is ALREADY applied at table-creation time via
``Base.metadata.create_all`` (see conftest.py), which reflects the
current state of the Trade model (including broker_ticket).

These tests verify the DB-level constraints match the migration spec.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


@pytest.mark.asyncio
async def test_broker_ticket_column_exists(db_session):
    """broker_ticket column exists on the trades table and is nullable TEXT."""
    result = await db_session.execute(text("PRAGMA table_info('trades')"))
    columns = {row.name: row for row in result}
    assert "broker_ticket" in columns
    col = columns["broker_ticket"]
    assert col.type.upper() == "TEXT"  # SQLite affinity
    assert col.notnull == 0  # nullable


@pytest.mark.asyncio
async def test_multiple_null_broker_tickets_allowed(db_session):
    """Multiple NULL broker_ticket values do NOT violate the unique index."""
    await db_session.execute(
        text(
            "INSERT INTO trades (account_id, asset_id, direction, status, "
            "entry_price, quantity, entry_datetime, created_at, commission, swap_fees, is_active, broker_ticket) "
            "VALUES (1, 1, 'long', 'closed', 100.0, 1.0, '2026-01-01T00:00:00', "
            "'2026-01-01T00:00:00', 0, 0, 1, NULL)"
        )
    )
    await db_session.execute(
        text(
            "INSERT INTO trades (account_id, asset_id, direction, status, "
            "entry_price, quantity, entry_datetime, created_at, commission, swap_fees, is_active, broker_ticket) "
            "VALUES (1, 1, 'long', 'closed', 100.0, 1.0, '2026-01-02T00:00:00', "
            "'2026-01-02T00:00:00', 0, 0, 1, NULL)"
        )
    )
    # Should not raise — multiple NULLs are allowed by partial unique index


@pytest.mark.asyncio
async def test_duplicate_broker_ticket_same_account_fails(db_session):
    """Same broker_ticket + same account_id raises IntegrityError."""
    await db_session.execute(
        text(
            "INSERT INTO trades (account_id, asset_id, direction, status, "
            "entry_price, quantity, entry_datetime, created_at, commission, swap_fees, is_active, broker_ticket) "
            "VALUES (1, 1, 'long', 'closed', 100.0, 1.0, '2026-01-01T00:00:00', "
            "'2026-01-01T00:00:00', 0, 0, 1, 'TKT-001')"
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.execute(
            text(
                "INSERT INTO trades (account_id, asset_id, direction, status, "
                "entry_price, quantity, entry_datetime, created_at, commission, swap_fees, is_active, broker_ticket) "
                "VALUES (1, 1, 'long', 'closed', 100.0, 1.0, '2026-01-02T00:00:00', "
                "'2026-01-02T00:00:00', 0, 0, 1, 'TKT-001')"
            )
        )


@pytest.mark.asyncio
async def test_same_ticket_different_accounts_allowed(db_session):
    """Same broker_ticket for DIFFERENT accounts is allowed."""
    await db_session.execute(
        text(
            "INSERT INTO trades (account_id, asset_id, direction, status, "
            "entry_price, quantity, entry_datetime, created_at, commission, swap_fees, is_active, broker_ticket) "
            "VALUES (1, 1, 'long', 'closed', 100.0, 1.0, '2026-01-01T00:00:00', "
            "'2026-01-01T00:00:00', 0, 0, 1, 'TKT-001')"
        )
    )
    # Different account_id (2) with same ticket — should succeed
    await db_session.execute(
        text(
            "INSERT INTO trades (account_id, asset_id, direction, status, "
            "entry_price, quantity, entry_datetime, created_at, commission, swap_fees, is_active, broker_ticket) "
            "VALUES (2, 1, 'long', 'closed', 100.0, 1.0, '2026-01-02T00:00:00', "
            "'2026-01-02T00:00:00', 0, 0, 1, 'TKT-001')"
        )
    )
    # No exception means success
