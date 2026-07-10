"""Integration tests verifying TIP domain integrity — tables, indexes, constraints, FKs, seeds.

All sync tests are wrapped in a per-function transaction that gets rolled back.
Async tests manage their own connections.
"""
# ruff: noqa: S101  -- allow assert in tests

from __future__ import annotations

import os
from time import perf_counter

import pytest
import sqlalchemy as sa
from sqlalchemy import event, text

from app.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_TABLES: list[str] = [
    "accounts",
    "alembic_version",
    "assets",
    "attachments",
    "brokers",
    "emotion_entries",
    "emotions",
    "market_sessions",
    "markets",
    "mistake_entries",
    "mistakes",
    "notes",
    "risk_profiles",
    "setups",
    "strategies",
    "strategy_setups",
    "tags",
    "timeframes",
    "trade_reviews",
    "trade_tags",
    "trades",
    "trading_sessions",
]

# SQLite creates indexes for UNIQUE constraints as ``sqlite_autoindex_*``
# rather than using the ``uq_`` names from the naming convention.
# Only explicit ``ix_`` indexes are listed below (20 total).
EXPECTED_IX_INDEXES: list[str] = [
    "ix_trades_account_id",
    "ix_trades_asset_id",
    "ix_trades_broker_id",
    "ix_trades_market_session_id",
    "ix_trades_timeframe_id",
    "ix_trades_strategy_id",
    "ix_trades_setup_id",
    "ix_trades_risk_profile_id",
    "ix_trades_trading_session_id",
    "ix_trades_entry_datetime",
    "ix_trades_exit_datetime",
    "ix_trades_status_entry_datetime",
    "ix_trades_asset_entry_datetime",
    "ix_trades_strategy_entry_datetime",
    "ix_trades_direction",
    "ix_emotion_entries_emotion_id",
    "ix_mistake_entries_mistake_id",
    "ix_trade_tags_tag_id",
    "ix_strategy_setups_setup_id",
    "ix_risk_profiles_strategy_id",
]

SEED_COUNTS: dict[str, int] = {
    "markets": 7,
    "market_sessions": 7,
    "timeframes": 10,
    "emotions": 12,
    "mistakes": 11,
    "brokers": 0,  # user-defined, not seeded
}

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def engine():
    """Sync SQLAlchemy engine with FK enforcement enabled."""
    e = sa.create_engine(f"sqlite:///{settings.db_path}")

    @event.listens_for(e, "connect")
    def _set_fk(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return e


@pytest.fixture(scope="function")
def conn(engine):
    """Wrap each test in a transaction that gets rolled back."""
    connection = engine.connect()
    trans = connection.begin()
    yield connection
    trans.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _setup_parents(conn) -> None:
    """Insert parent rows needed for constraint / FK tests.

    Raw SQL inserts must provide every NOT NULL column because server defaults
    are only applied by the ORM, not by the SQLite schema itself.
    """
    ts = "'2026-01-01T00:00:00Z'"
    # Account (has is_active NOT NULL)
    conn.execute(
        text(
            "INSERT INTO accounts (id, name, status, base_currency, created_at, is_active) "
            f"VALUES (900, 'test_acct', 'active', 'USD', {ts}, 1)"
        )
    )
    # Asset (market_id=1 = 'forex' from seeds, has is_active NOT NULL)
    conn.execute(
        text(
            f"INSERT INTO assets (id, symbol, name, market_id, created_at, is_active) "
            f"VALUES (900, 'TEST', 'Test Asset', 1, {ts}, 1)"
        )
    )
    # Emotion
    conn.execute(
        text(f"INSERT INTO emotions (id, name, created_at) VALUES (900, 'test_emotion', {ts})")
    )
    # Mistake
    conn.execute(
        text(f"INSERT INTO mistakes (id, name, created_at) VALUES (900, 'test_mistake', {ts})")
    )
    # Tag
    conn.execute(text(f"INSERT INTO tags (id, name, created_at) VALUES (900, 'test_tag', {ts})"))
    # TradingSession (has is_active NOT NULL)
    conn.execute(
        text(
            f"INSERT INTO trading_sessions (id, name, start_datetime, created_at, is_active) "
            f"VALUES (900, 'test_session', {ts}, {ts}, 1)"
        )
    )
    # Strategy (has is_active NOT NULL)
    conn.execute(
        text(
            f"INSERT INTO strategies (id, name, created_at, is_active) "
            f"VALUES (900, 'test_strategy', {ts}, 1)"
        )
    )
    # Setup (has is_active NOT NULL)
    conn.execute(
        text(
            f"INSERT INTO setups (id, name, created_at, is_active) "
            f"VALUES (900, 'test_setup', {ts}, 1)"
        )
    )
    # RiskProfile (has is_active NOT NULL)
    conn.execute(
        text(
            f"INSERT INTO risk_profiles (id, name, created_at, is_active) "
            f"VALUES (900, 'test_rp', {ts}, 1)"
        )
    )


def _create_trade(conn, *, extra_cols: str = "", extra_vals: str = "") -> int:
    """Insert a valid trade with optional extras; return its id.

    Must provide ``commission``, ``swap_fees``, ``created_at``, ``is_active``
    explicitly because ORM-side defaults are not applied by raw SQL inserts.
    """
    ts = "'2026-01-01T00:00:00Z'"
    conn.execute(
        text(
            "INSERT INTO trades "
            "(id, account_id, asset_id, direction, status, entry_price, quantity, "
            "entry_datetime, commission, swap_fees, created_at, is_active"
            f"{extra_cols}) "
            "VALUES "
            f"(901, 900, 900, 'long', 'open', 1.0, 1.0, {ts}, 0.0, 0.0, {ts}, 1"
            f"{extra_vals})"
        )
    )
    return 901


# ---------------------------------------------------------------------------
# Parametrized CHECK violation cases
# ---------------------------------------------------------------------------

_BASE_TRADE_COLS = (
    "account_id, asset_id, direction, status, entry_price, "
    "quantity, entry_datetime, commission, swap_fees, created_at, is_active"
)
_TS = "'2026-01-01T00:00:00Z'"
_BASE_TRADE_VALS = f"900, 900, 'long', 'open', 1.0, 1.0, {_TS}, 0.0, 0.0, {_TS}, 1"

TRADE_VIOLATIONS: list[tuple[str, str]] = [
    # (SQL, description)
    (
        f"INSERT INTO trades ({_BASE_TRADE_COLS}) VALUES "
        f"(900, 900, 'invalid', 'open', 1.0, 1.0, {_TS}, 0.0, 0.0, {_TS}, 1)",
        "direction invalid",
    ),
    (
        f"INSERT INTO trades ({_BASE_TRADE_COLS}) VALUES "
        f"(900, 900, 'long', 'invalid', 1.0, 1.0, {_TS}, 0.0, 0.0, {_TS}, 1)",
        "status invalid",
    ),
    (
        f"INSERT INTO trades ({_BASE_TRADE_COLS}) VALUES "
        f"(900, 900, 'long', 'open', 0, 1.0, {_TS}, 0.0, 0.0, {_TS}, 1)",
        "entry_price zero",
    ),
    (
        f"INSERT INTO trades ({_BASE_TRADE_COLS}) VALUES "
        f"(900, 900, 'long', 'open', -1, 1.0, {_TS}, 0.0, 0.0, {_TS}, 1)",
        "entry_price negative",
    ),
    (
        f"INSERT INTO trades ({_BASE_TRADE_COLS}) VALUES "
        f"(900, 900, 'long', 'open', 1.0, 0, {_TS}, 0.0, 0.0, {_TS}, 1)",
        "quantity zero",
    ),
    (
        "INSERT INTO trades (account_id, asset_id, direction, status, entry_price, "
        "quantity, position_size, entry_datetime, commission, swap_fees, created_at, "
        "is_active) "
        f"VALUES (900, 900, 'long', 'open', 1.0, 1.0, -1, {_TS}, 0.0, 0.0, {_TS}, 1)",
        "position_size negative",
    ),
    (
        f"INSERT INTO trades ({_BASE_TRADE_COLS}) VALUES "
        f"(900, 900, 'long', 'open', 1.0, 1.0, {_TS}, -1, 0.0, {_TS}, 1)",
        "commission negative",
    ),
    (
        f"INSERT INTO trades ({_BASE_TRADE_COLS}) VALUES "
        f"(900, 900, 'long', 'open', 1.0, 1.0, {_TS}, 0.0, -1, {_TS}, 1)",
        "swap_fees negative",
    ),
]

_EE = f"901, 900, 5, 'during_trade', {_TS}"

EMOTION_VIOLATIONS: list[tuple[str, str]] = [
    (
        f"INSERT INTO emotion_entries (trade_id, emotion_id, intensity, context, created_at) "
        f"VALUES (901, 900, 0, 'during_trade', {_TS})",
        "intensity zero",
    ),
    (
        f"INSERT INTO emotion_entries (trade_id, emotion_id, intensity, context, created_at) "
        f"VALUES (901, 900, 11, 'during_trade', {_TS})",
        "intensity above 10",
    ),
    (
        f"INSERT INTO emotion_entries (trade_id, emotion_id, intensity, context, created_at) "
        f"VALUES (901, 900, 5, 'invalid_context', {_TS})",
        "context invalid",
    ),
]

ATTACHMENT_VIOLATIONS: list[tuple[str, str]] = [
    (
        f"INSERT INTO attachments (trade_id, file_path, type, created_at, is_active, sort_order) "
        f"VALUES (901, '/tmp/test.pdf', 'pdf', {_TS}, 1, 0)",
        "type pdf not allowed (only 'image' for MVP)",
    ),
]

ACCOUNT_VIOLATIONS: list[tuple[str, str]] = [
    (
        f"INSERT INTO accounts (name, status, base_currency, created_at, is_active) "
        f"VALUES ('bad_acct', 'invalid', 'USD', {_TS}, 1)",
        "status invalid",
    ),
]

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFullDomainIntegrity:
    """Comprehensive domain integrity tests — all wrapped in rolled-back transactions."""

    # -- 5.3 Table count ---------------------------------------------------

    def test_table_count(self, conn):
        """Verify exactly 22 tables (21 domain + alembic_version)."""
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ).fetchall()
        names = [r[0] for r in rows]
        assert names == EXPECTED_TABLES, f"Got {len(names)} tables: {names}"

    # -- 5.4 Index existence -----------------------------------------------

    def test_index_count(self, conn):
        """Verify all expected indexes exist.

        SQLite creates internal autoindexes for UNIQUE and PK constraints
        (``sqlite_autoindex_*``). We verify total index count >= 28
        (Design §5) and check every explicit ``ix_`` index by name.
        """
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
        ).fetchall()
        index_names = {r[0] for r in rows}
        assert len(index_names) >= 28, f"Got {len(index_names)} indexes, expected >= 28"
        for idx in EXPECTED_IX_INDEXES:
            assert idx in index_names, f"Missing index: {idx}"

    # -- 5.5 CHECK constraints ---------------------------------------------

    @pytest.mark.parametrize("sql,desc", TRADE_VIOLATIONS)
    def test_trade_check_violations(self, conn, sql, desc):
        _setup_parents(conn)
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(text(sql))

    @pytest.mark.parametrize("sql,desc", EMOTION_VIOLATIONS)
    def test_emotion_entry_check_violations(self, conn, sql, desc):
        _setup_parents(conn)
        _create_trade(conn)
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(text(sql))

    @pytest.mark.parametrize("sql,desc", ATTACHMENT_VIOLATIONS)
    def test_attachment_check_violations(self, conn, sql, desc):
        _setup_parents(conn)
        _create_trade(conn)
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(text(sql))

    @pytest.mark.parametrize("sql,desc", ACCOUNT_VIOLATIONS)
    def test_account_check_violations(self, conn, sql, desc):
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(text(sql))

    def test_valid_trade_insert_succeeds(self, conn):
        """Valid INSERT with all proper values should succeed."""
        _setup_parents(conn)
        _create_trade(conn)
        # Verify the trade was inserted
        count = conn.execute(text("SELECT COUNT(*) FROM trades WHERE id = 901")).scalar()
        assert count == 1

    # -- 5.6 FK CASCADE ----------------------------------------------------

    def test_fk_cascade(self, conn):
        """Delete from trades cascades to emotion_entries, mistake_entries,
        notes, trade_reviews, attachments, trade_tags."""
        _setup_parents(conn)
        _create_trade(conn)

        # Create child rows (provide all NOT NULL columns)
        conn.execute(
            text(
                "INSERT INTO emotion_entries (trade_id, emotion_id, intensity, "
                "context, created_at) "
                f"VALUES (901, 900, 5, 'during_trade', {_TS})"
            )
        )
        conn.execute(
            text(
                "INSERT INTO mistake_entries (trade_id, mistake_id, created_at) "
                f"VALUES (901, 900, {_TS})"
            )
        )
        conn.execute(
            text(
                "INSERT INTO notes (trade_id, content, created_at) "
                f"VALUES (901, 'test note', {_TS})"
            )
        )
        conn.execute(
            text(
                "INSERT INTO trade_reviews (trade_id, content, created_at) "
                f"VALUES (901, 'test review', {_TS})"
            )
        )
        conn.execute(
            text(
                "INSERT INTO attachments (trade_id, file_path, type, created_at, "
                "is_active, sort_order) "
                f"VALUES (901, '/tmp/test.png', 'image', {_TS}, 1, 0)"
            )
        )
        conn.execute(text("INSERT INTO trade_tags (trade_id, tag_id) VALUES (901, 900)"))

        # Verify children exist before cascade
        assert (
            conn.execute(text("SELECT COUNT(*) FROM emotion_entries WHERE trade_id = 901")).scalar()
            == 1
        )
        assert (
            conn.execute(text("SELECT COUNT(*) FROM mistake_entries WHERE trade_id = 901")).scalar()
            == 1
        )
        assert conn.execute(text("SELECT COUNT(*) FROM notes WHERE trade_id = 901")).scalar() == 1
        assert (
            conn.execute(text("SELECT COUNT(*) FROM trade_reviews WHERE trade_id = 901")).scalar()
            == 1
        )
        assert (
            conn.execute(text("SELECT COUNT(*) FROM attachments WHERE trade_id = 901")).scalar()
            == 1
        )
        assert (
            conn.execute(text("SELECT COUNT(*) FROM trade_tags WHERE trade_id = 901")).scalar() == 1
        )

        # Delete the trade via direct SQL
        conn.execute(text("DELETE FROM trades WHERE id = 901"))

        # Verify all children cascade-deleted
        assert (
            conn.execute(text("SELECT COUNT(*) FROM emotion_entries WHERE trade_id = 901")).scalar()
            == 0
        )
        assert (
            conn.execute(text("SELECT COUNT(*) FROM mistake_entries WHERE trade_id = 901")).scalar()
            == 0
        )
        assert conn.execute(text("SELECT COUNT(*) FROM notes WHERE trade_id = 901")).scalar() == 0
        assert (
            conn.execute(text("SELECT COUNT(*) FROM trade_reviews WHERE trade_id = 901")).scalar()
            == 0
        )
        assert (
            conn.execute(text("SELECT COUNT(*) FROM attachments WHERE trade_id = 901")).scalar()
            == 0
        )
        assert (
            conn.execute(text("SELECT COUNT(*) FROM trade_tags WHERE trade_id = 901")).scalar() == 0
        )

    # -- 5.7 FK RESTRICT ---------------------------------------------------

    def test_fk_restrict_asset(self, conn):
        """Delete asset with trades → IntegrityError."""
        _setup_parents(conn)
        _create_trade(conn)
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(text("DELETE FROM assets WHERE id = 900"))

    def test_fk_restrict_emotion(self, conn):
        """Delete emotion with entries → IntegrityError."""
        _setup_parents(conn)
        _create_trade(conn)
        conn.execute(
            text(
                "INSERT INTO emotion_entries (trade_id, emotion_id, intensity, "
                "context, created_at) "
                f"VALUES (901, 900, 5, 'during_trade', {_TS})"
            )
        )
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(text("DELETE FROM emotions WHERE id = 900"))

    def test_fk_restrict_tag(self, conn):
        """Delete tag with trade_tags → IntegrityError."""
        _setup_parents(conn)
        _create_trade(conn)
        conn.execute(text("INSERT INTO trade_tags (trade_id, tag_id) VALUES (901, 900)"))
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(text("DELETE FROM tags WHERE id = 900"))

    def test_fk_restrict_mistake(self, conn):
        """Delete mistake with entries → IntegrityError."""
        _setup_parents(conn)
        _create_trade(conn)
        conn.execute(
            text(
                "INSERT INTO mistake_entries (trade_id, mistake_id, created_at) "
                f"VALUES (901, 900, {_TS})"
            )
        )
        with pytest.raises(sa.exc.IntegrityError):
            conn.execute(text("DELETE FROM mistakes WHERE id = 900"))

    # -- 5.8 FK SET NULL ---------------------------------------------------

    def _test_set_null(self, conn, parent_table: str, parent_id_col: str, parent_id: int) -> None:
        """Helper: delete a parent row and verify FK is NULLed on trades."""
        conn.execute(text(f"DELETE FROM {parent_table} WHERE id = {parent_id}"))
        result = conn.execute(text(f"SELECT {parent_id_col} FROM trades WHERE id = 901")).scalar()
        assert result is None, f"{parent_id_col} should be NULL after parent delete"

    def test_fk_set_null_trading_session(self, conn):
        _setup_parents(conn)
        _create_trade(conn, extra_cols=", trading_session_id", extra_vals=", 900")
        self._test_set_null(conn, "trading_sessions", "trading_session_id", 900)

    def test_fk_set_null_strategy(self, conn):
        _setup_parents(conn)
        _create_trade(conn, extra_cols=", strategy_id", extra_vals=", 900")
        self._test_set_null(conn, "strategies", "strategy_id", 900)

    def test_fk_set_null_risk_profile(self, conn):
        _setup_parents(conn)
        _create_trade(conn, extra_cols=", risk_profile_id", extra_vals=", 900")
        self._test_set_null(conn, "risk_profiles", "risk_profile_id", 900)

    def test_fk_set_null_setup(self, conn):
        _setup_parents(conn)
        _create_trade(conn, extra_cols=", setup_id", extra_vals=", 900")
        self._test_set_null(conn, "setups", "setup_id", 900)

    # -- 5.9 Seed row counts -----------------------------------------------

    def test_seed_row_counts(self, conn):
        """Verify each seeded catalog table has the expected row count."""
        for table, expected in SEED_COUNTS.items():
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count == expected, f"{table}: expected {expected} rows, got {count}"

    # -- 5.10 Seed idempotency ---------------------------------------------

    def test_seed_idempotency(self, conn):
        """Re-inserting seed data via INSERT OR IGNORE does not change counts."""
        # Re-insert all markets
        for name in ["forex", "indices", "commodities", "crypto", "equities", "bonds", "etfs"]:
            conn.execute(
                text("INSERT OR IGNORE INTO markets (name) VALUES (:n)"),
                {"n": name},
            )
        # Re-insert all market_sessions
        for name in [
            "asian",
            "european",
            "american",
            "asian_european_overlap",
            "european_american_overlap",
            "weekend",
            "opening_auction",
        ]:
            conn.execute(
                text("INSERT OR IGNORE INTO market_sessions (name) VALUES (:n)"),
                {"n": name},
            )
        # Re-insert all timeframes
        for name in ["M1", "M5", "M15", "M30", "H1", "H2", "H4", "D1", "W1", "MN"]:
            conn.execute(
                text("INSERT OR IGNORE INTO timeframes (name) VALUES (:n)"),
                {"n": name},
            )
        # Re-insert all emotions
        for name in [
            "calm",
            "anxious",
            "confident",
            "fearful",
            "greedy",
            "neutral",
            "excited",
            "frustrated",
            "disappointed",
            "apathetic",
            "hopeful",
            "regretful",
        ]:
            conn.execute(
                text("INSERT OR IGNORE INTO emotions (name) VALUES (:n)"),
                {"n": name},
            )
        # Re-insert all mistakes
        for name in [
            "fomo",
            "revenge_trading",
            "overtrading",
            "no_stop_loss",
            "moving_stop_loss",
            "holding_losers",
            "cutting_winners",
            "ignoring_risk",
            "bad_entry",
            "no_plan",
            "emotional_trading",
        ]:
            conn.execute(
                text("INSERT OR IGNORE INTO mistakes (name) VALUES (:n)"),
                {"n": name},
            )
        # Verify counts unchanged
        for table, expected in SEED_COUNTS.items():
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count == expected, (
                f"{table}: expected {expected} rows after re-insert, got {count}"
            )

    # -- 5.11 PRAGMA foreign_keys ------------------------------------------

    def test_pragma_foreign_keys_on(self, conn):
        """Verify PRAGMA foreign_keys = ON."""
        row = conn.execute(text("PRAGMA foreign_keys")).fetchone()
        assert row is not None
        assert row[0] == 1

    # -- 5.12 Alembic clean install (DESTRUCTIVE — skipped by default) -----

    @pytest.mark.skipif(
        not os.getenv("ALEMBIC_CLEAN_TEST"),
        reason="Destructive - set ALEMBIC_CLEAN_TEST=1 to run",
    )
    def test_alembic_clean_install(self):
        """Remove DB, run alembic upgrade head, verify 22 tables."""
        import subprocess
        import sys

        db_path = settings.db_path
        if os.path.exists(db_path):
            os.remove(db_path)

        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__) + "/..",
        )
        assert result.returncode == 0, f"alembic upgrade head failed:\n{result.stderr}"

        # Verify tables
        e = sa.create_engine(f"sqlite:///{db_path}")
        with e.connect() as c:
            rows = c.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            ).fetchall()
            names = [r[0] for r in rows]
            assert len(names) == 22, f"Expected 22 tables, got {len(names)}: {names}"

    # -- 5.13 Join performance smoke test ----------------------------------

    def test_join_performance(self, conn):
        """Basic JOIN query completes in under 100ms on empty DB."""
        start = perf_counter()
        conn.execute(
            text(
                "SELECT t.id, a.symbol, m.name as market "
                "FROM trades t "
                "JOIN assets a ON t.asset_id = a.id "
                "JOIN markets m ON a.market_id = m.id "
                "LIMIT 10"
            )
        ).fetchall()
        elapsed = (perf_counter() - start) * 1000
        assert elapsed < 100, f"JOIN query took {elapsed:.1f}ms (expected <100ms)"


# -- Async PRAGMA check ------------------------------------------------------


@pytest.mark.asyncio
async def test_pragma_async():
    """Verify PRAGMA foreign_keys = ON via async engine."""
    from app.database import engine as async_engine

    async with async_engine.connect() as conn:
        result = await conn.exec_driver_sql("PRAGMA foreign_keys")
        row = result.fetchone()
        assert row is not None
        assert row[0] == 1
