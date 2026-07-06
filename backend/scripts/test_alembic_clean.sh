#!/usr/bin/env bash
# Destructive test: remove DB, run alembic upgrade head, verify 22 tables.
# Must be run from the backend/ directory.
set -euo pipefail

cd "$(dirname "$0")/.."
echo "=== Clean-install test ==="

DB_PATH="../data/tip.db"
echo "Removing $DB_PATH..."
rm -f "$DB_PATH"

echo "Running: alembic upgrade head..."
alembic upgrade head

echo "Verifying 22 tables..."
TABLE_COUNT=$(python3 -c "
from sqlalchemy import create_engine, text
engine = create_engine('sqlite:///../data/tip.db')
with engine.connect() as c:
    r = c.execute(text(\"SELECT count(*) FROM sqlite_master WHERE type='table'\")).scalar()
    print(r)
")
echo "Tables: $TABLE_COUNT (expected 22)"

if [ "$TABLE_COUNT" -eq 22 ]; then
    echo "SUCCESS: Clean install yields $TABLE_COUNT tables."
    exit 0
else
    echo "FAILURE: Expected 22 tables, got $TABLE_COUNT."
    exit 1
fi
