"""Strategy Lab test fixtures.

Installs SQLite immutability triggers on the in-memory test DB
(since tests use ``Base.metadata.create_all``, not alembic migrations).
"""

import pytest_asyncio
from sqlalchemy import text


@pytest_asyncio.fixture(autouse=True)
async def install_immutability_triggers(db_session):
    """Install immutability triggers on every test's DB session.

    The in-memory test DB is created via ``Base.metadata.create_all``,
    which skips alembic migrations. We install the triggers manually
    to match the production schema.
    """
    await db_session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS trg_run_immutable_update
            BEFORE UPDATE ON runs
            BEGIN
                SELECT RAISE(ABORT, 'Runs are immutable - cannot UPDATE');
            END;
            """
        )
    )
    await db_session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS trg_run_immutable_delete
            BEFORE DELETE ON runs
            BEGIN
                SELECT RAISE(ABORT, 'Runs are immutable - cannot DELETE');
            END;
            """
        )
    )
    await db_session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS trg_run_metric_immutable_update
            BEFORE UPDATE ON run_metrics
            BEGIN
                SELECT RAISE(ABORT, 'RunMetrics are immutable - cannot UPDATE');
            END;
            """
        )
    )
    await db_session.execute(
        text(
            """
            CREATE TRIGGER IF NOT EXISTS trg_run_metric_immutable_delete
            BEFORE DELETE ON run_metrics
            BEGIN
                SELECT RAISE(ABORT, 'RunMetrics are immutable - cannot DELETE');
            END;
            """
        )
    )
    await db_session.commit()
