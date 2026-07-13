# ADR-010: Edge Discovery Snapshots are Versioned and Reproducible

## Status

Accepted

## Context

Edge Discovery runs computationally expensive statistical procedures: bootstrap resampling (10K iterations per group), FDR correction across all groups, and split-half stability tests. With hundreds of dimension combinations, a single generation run takes seconds to tens of seconds. Running this computation on every request is unacceptable.

We also need:
- **Reproducibility**: given the same parameters and trade dataset, the output must be identical. This enables debugging, audit, and comparison.
- **Audit trail**: traders need to see what changed when edges are re-generated — was it the data or the parameters?
- **Drill-down**: endpoints must query individual edges, not re-recompute them.
- **Time-travel**: ability to compare "last week's edges" with "this week's edges" to see how edges evolve.

SQLite was chosen as the storage backend (per pre-closed Decision 2) — not in-memory (survives restarts), not a plain file (queryable by group_id).

## Decision

Every call to `EdgeDiscoveryEngine.generate()` produces an immutable **snapshot** stored in a dedicated `edge_snapshots` table in a local SQLite database (`data/edge_cache.db`).

### Table Schema

```sql
CREATE TABLE IF NOT EXISTS edge_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    parameters TEXT NOT NULL,    -- JSON
    results TEXT NOT NULL        -- JSON array of EdgeScore records
);
```

- `snapshot_id`: UUID v4, generated at the start of `generate()`
- `created_at`: ISO 8601 timestamp when generation began
- `parameters`: JSON object with all generation parameters (`min_observations`, `bootstrap_resamples`, `fdr_alpha`, `stability_threshold`, `seed`, `version`)
- `results`: JSON array of all `EdgeScore` records computed (including those that fail the statistical gate)

### Behavior

- **Immutable**: once stored, a snapshot is never modified. Re-generation creates a new snapshot with a new UUID.
- **Latest snapshot**: `GET /analytics/edges` always returns the latest snapshot (sorted by `created_at DESC`).
- **Version listing**: `GET /analytics/edges/snapshots` lists all snapshots with metadata.
- **Time-travel**: `GET /analytics/edges/snapshots/{id}` retrieves a specific version.
- **Reproducibility**: the same parameters + same seed + same trade dataset produce identical results. The seed is part of `parameters`.
- **Group query**: `GET /analytics/edges/{group_id}` queries the latest snapshot's results by group_id (JSON extraction within SQLite, or filter in Python after loading results).

### Storage Details

- Database path: `data/edge_cache.db` (relative to project root)
- Connection managed by `SqliteEdgeRepository` with lazy initialization
- Uses `aiosqlite` for async access (consistent with FastAPI async stack)
- The results JSON is parsed with Pydantic on read for type safety

### Query Patterns

```python
# Save
INSERT INTO edge_snapshots (snapshot_id, created_at, parameters, results)
VALUES (?, ?, ?, ?)

# Latest snapshot
SELECT results FROM edge_snapshots
ORDER BY created_at DESC LIMIT 1

# Specific snapshot
SELECT results FROM edge_snapshots WHERE snapshot_id = ?

# List snapshots
SELECT snapshot_id, created_at, parameters
FROM edge_snapshots ORDER BY created_at DESC
```

### What is NOT stored

- Raw trade data is NOT duplicated in the cache — `trade_ids` references primary keys in the main database.
- Intermediate computation artifacts (bootstrap distributions, per-resample metrics) are NOT persisted — only the final EdgeScore records.

## Consequences

### Positive

- ✅ **Read endpoints are fast** — they query SQLite JSON, which is O(1) for a single row lookup (latest snapshot) vs. O(N×resamples) for recomputation.
- ✅ **Full audit trail** — every generation creates a new snapshot with metadata. Traders can see how edges evolve over time.
- ✅ **Reproducible debugging** — given snapshot_id + seed, the output is deterministic. Bugs can be traced to specific parameters.
- ✅ **No migration to main DB** — the cache is a separate SQLite file. No schema changes to trades, accounts, or catalogs.
- ✅ **Survives restarts** — snapshots persist across application restarts. No warm-up needed.
- ✅ **Background generation** — the POST endpoint triggers async generation that writes directly to SQLite. The user polls or refreshes to see new results.

### Negative

- ❌ **Snapshot is a point-in-time copy** — if trades are edited or deleted after snapshot creation, the snapshot's `trade_ids` may reference trades that no longer match the current data. This is acceptable for an analytical cache (the snapshot represents "edges at that point in time"), but must be documented.
- ❌ **Results JSON can be large** — for 500+ edge groups, the JSON can be multiple MB. Mitigation: partial reads via SQLite JSON functions for single-edge queries (extract element from array), or post-load filtering in Python. The full snapshot is fetched for the ranking list endpoint, which is paginated at the application layer.
- ❌ **No live cache invalidation** — snapshots must be manually re-generated after new trades are imported. Mitigation: the `generated_at` timestamp is displayed in the UI so traders know the data age. A future enhancement could auto-trigger generation after import.
