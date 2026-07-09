# SDD Spec: Trading Journal MVP

**Change:** `trading-journal-mvp`
**Phase:** Spec
**Status:** Draft
**Date:** 2026-07-09

---

## 1. API Contracts

### 1.1 `GET /api/trades`

Paginated, filterable, sortable, searchable trade list. All query parameters are optional.

#### Query Parameters

| Param | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `page` | `int` | `1` | `>= 1` | Page number (1-indexed) |
| `page_size` | `int` | `20` | `1 <= n <= 100` | Items per page |
| `account_id` | `int` | — | — | Filter by account FK |
| `asset_id` | `int` | — | — | Filter by asset FK |
| `direction` | `str` | — | `"long"` \| `"short"` | Filter by trade direction |
| `status` | `str` | — | `"open"` \| `"closed"` | Filter by trade status (omitting returns both) |
| `date_from` | `str` | — | ISO 8601 datetime | `entry_datetime >= date_from` |
| `date_to` | `str` | — | ISO 8601 datetime | `entry_datetime <= date_to` |
| `search` | `str` | — | Free text | OR-match across `broker_ticket`, `asset.symbol`, `notes_override` (ILIKE, see §1.4) |
| `sort_by` | `str` | `entry_datetime` | Whitelist (see §1.3) | Sort column |
| `sort_dir` | `str` | `desc` | `"asc"` \| `"desc"` | Sort direction |

**Validation:**
- `sort_by` outside the whitelist → **422 Unprocessable Entity** with descriptive error.
- `sort_dir` not in `{"asc", "desc"}` → **422 Unprocessable Entity** (FastAPI `Literal` validation).
- `page_size > 100` → **422 Unprocessable Entity** (Pydantic `le=100`).

#### Response Body

```json
{
  "items": [ TradeResponse, ... ],
  "total": 342,
  "page": 1,
  "page_size": 20,
  "pages": 18
}
```

**Field definitions:**

| Field | Type | Description |
|-------|------|-------------|
| `items` | `list[TradeResponse]` | The page of results |
| `total` | `int` | Total matching records across all pages (not capped by `page_size`) |
| `page` | `int` | Current page number (echoed from request) |
| `page_size` | `int` | Items per page (echoed from request) |
| `pages` | `int` | Total pages computed as `ceil(total / page_size)`, minimum 1 |

> **Note:** The response envelope field is `pages`, not `total_pages`. This matches the existing `PaginatedResponse` schema at `backend/app/modules/shared/pagination.py:33`.

### 1.2 `GET /api/trades/summary`

Aggregated statistics scoped to the **same filter parameters** as `GET /api/trades` (all filter params listed in §1.1 apply — `account_id`, `asset_id`, `direction`, `status`, `date_from`, `date_to`, `search`).

**No pagination, no sort parameters.** `page`, `page_size`, `sort_by`, `sort_dir` are rejected with 422.

#### Response Body

```json
{
  "total_trades": 342,
  "net_pnl": 12450.75,
  "win_rate": 0.62
}
```

**Field definitions:**

| Field | Type | Description |
|-------|------|-------------|
| `total_trades` | `int` | Count of trades matching the filter criteria |
| `net_pnl` | `float` | Sum of net P&L for closed trades within the filtered set (open trades contribute 0). Formula per trade: `(exit_price - entry_price) * quantity * direction_sign - commission - swap_fees` |
| `win_rate` | `float` | Ratio of profitable closed trades to total closed trades within the filtered set. `None` when there are zero closed trades. |

**Computation detail (backend):**
- `net_pnl` = `SUM(CASE WHEN status='closed' THEN computed_pnl ELSE 0 END)` — computed via SQL `CASE` expressions, not Python iteration.
- `win_rate` = `COUNT(CASE WHEN status='closed' AND computed_pnl > 0 THEN 1 END) / NULLIF(COUNT(CASE WHEN status='closed' THEN 1 END), 0)` — returns `None` when denominator is zero.
- `computed_pnl` = `CASE WHEN direction='long' THEN (exit_price - entry_price) * quantity ELSE (entry_price - exit_price) * quantity END - COALESCE(commission, 0) - ABS(COALESCE(swap_fees, 0))`
- All arithmetic uses SQL-level expressions via `sqlalchemy.func` and `sqlalchemy.case` — no Python loops.

### 1.3 Sort Behavior

- `sort_by` is restricted to a **whitelist** of column aliases:

  | Sort Key | SQL Target | Notes |
  |----------|-----------|-------|
  | `entry_datetime` | `Trade.entry_datetime` | Default |
  | `exit_datetime` | `Trade.exit_datetime` | |
  | `net_pnl` | Computed PnL expression | Requires CASE expression in ORDER BY, same formula as §1.2 |
  | `symbol` | `Asset.symbol` | Requires join to `Asset` |
  | `broker_ticket` | `Trade.broker_ticket` | |

- Invalid `sort_by` values are rejected with **422**.
- Default: `sort_by=entry_datetime`, `sort_dir=desc`.
- **Tiebreaker**: Always append `Trade.id DESC` to the ORDER BY clause (see REQ-SPEC-02).

### 1.4 Search Behavior

- The `search` parameter performs a **case-insensitive OR** match across three text columns:
  - `Trade.broker_ticket` (`ILIKE '%{search}%'`)
  - `Asset.symbol` (`ILIKE '%{search}%'`) — requires join to `Asset`
  - `Trade.notes_override` (`ILIKE '%{search}%'`)
- All three conditions are wrapped in an `OR` at the query level.
- No numeric/date field search.
- The join to `Asset` for search is shared with the `sort_by=symbol` case — the join happens at most once.
- The search filter adds to the `WHERE` clause via `OR` (not `AND` with other filters — search is additive).

### 1.5 Schema Changes

#### `TradeFilters` (backend/app/modules/trades/schemas.py)

**Add:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sort_by` | `str \| None` | `None` | Sort column alias; validated against whitelist in service |
| `sort_dir` | `Literal["asc", "desc"] \| None` | `None` | Sort direction |

Default behavior when both are `None`: `sort_by=entry_datetime`, `sort_dir=desc` (applied in `TradeService.list()`).

#### `TradeResponse` (backend/app/modules/trades/schemas.py)

**Add field:**

| Field | Type | Description |
|-------|------|-------------|
| `broker_ticket` | `str \| None` | Broker ticket reference, nullable (mapped from `Trade.broker_ticket`) |

#### `SummaryResponse` (new schema)

New Pydantic model in `backend/app/modules/trades/schemas.py`:

```python
class TradeSummaryResponse(BaseModel):
    total_trades: int
    net_pnl: float
    win_rate: float | None
```

---

## 2. REQ-SPEC-01: Pagination Reset on Filter Change

**Requirement:** When any filter parameter changes (`account_id`, `asset_id`, `direction`, `status`, `date_from`, `date_to`, `search`), the frontend MUST reset `page` to 1.

**Rationale:** If a user is on page 8 of a 15-page result set and changes to a filter that only has 2 pages, they would see an empty page without this reset. The reset ensures the user always sees valid (non-empty) pages.

**Affected components:**
- Trade list hook (`useTrades` or equivalent) — must reset `page` to 1 when any filter value changes.
- URL-synced filter hook — must clear or reset the `page` URL param when any filter key changes.

**Interaction rule:** The page parameter change triggers a new API request automatically. The reset is evaluated BEFORE the API call — the request URL should have `page=1` whenever a non-page filter changes.

### Scenario 1: Account filter reduces page count

**Given** a user is viewing the trade list on page 8 with "all accounts" selected  
**When** they change the account filter to a specific account that has only 2 pages of trades  
**Then** the page parameter resets to 1  
**And** the UI shows page 1 of the new result set  
**And** no empty-state or error is shown due to invalid page

### Scenario 2: Search query resets deep pagination

**Given** a user is on page 3 of the unfiltered trade list  
**When** they type a search query that matches only 5 rows (1 page worth)  
**Then** the page parameter resets to 1  
**And** the UI shows the 5 matching results  
**And** the pagination controls show "Page 1 of 1"

### Scenario 3: Filter change while on page 1

**Given** a user is on page 1 with a date range filter active  
**When** they change the date range  
**Then** the page parameter stays at 1 (reset is idempotent — 1 → 1)  
**And** the new results are fetched immediately

### Implementation guidance

The page reset logic lives in the **hook** that manages trade queries, not in individual components. Pattern:

```js
// Pseudo: inside useTrades hook
const filters = { account_id, asset_id, direction, status, date_from, date_to, search };
const [page, setPage] = useState(1);

// Reset page when any non-page filter changes
useEffect(() => {
  setPage(1);
}, [filters.account_id, filters.asset_id, filters.direction, filters.status,
    filters.date_from, filters.date_to, filters.search]);
```

---

## 3. REQ-SPEC-02: Stable Sort Tiebreaker

**Requirement:** When two or more trades have the identical value in the `sort_by` column, the backend MUST apply a deterministic secondary sort to prevent trades from "jumping" between pages across requests.

**Rule:** Append `Trade.id DESC` to every ORDER BY clause generated by `TradeRepository.list()`.

```sql
-- Example: sort_by=entry_datetime, sort_dir=desc
ORDER BY trades.entry_datetime DESC, trades.id DESC

-- Example: sort_by=net_pnl, sort_dir=asc
ORDER BY computed_pnl ASC, trades.id DESC
```

**Rationale:** Without a tiebreaker, rows with identical `entry_datetime` (same-second trades) can appear in arbitrary order. When paginating, a trade on page 2's last row could "jump" to page 3 or back to page 1 on the next request, causing UX flicker and potential double-count/skip issues.

**Affected component:** `TradeRepository.list()` in `backend/app/modules/trades/repository.py`.

### Scenario 1: Same-second trades — next page

**Given** the trade list is sorted by `entry_datetime DESC`  
**And** there are 25 trades with `entry_datetime = "2026-01-15T10:30:00"`  
**When** the user requests `page_size=20`, `page=1`  
**Then** the first 20 of those 25 trades are returned, ordered deterministically by `id DESC`  
**And** when requesting `page=2`, the remaining 5 trades are returned  
**And** no trade appears on both pages or is skipped

### Scenario 2: Sort by PnL with ties

**Given** the trade list is sorted by `net_pnl ASC`  
**And** multiple trades have net PnL = 0.00  
**When** paginating through results  
**Then** the order among zero-PnL trades is stable (determined by `id DESC`)  
**And** repeated requests for the same page return the same trades in the same order

### Implementation guidance

The tiebreaker is appended unconditionally inside `TradeRepository.list()` — it is NOT exposed as a user-facing parameter. The SQLAlchemy expression is:

```python
order_by = [sort_column, Trade.id.desc()]
```

---

## 4. Acceptance Criteria Scenarios

### AC-01: Basic list (no filters)

**Given** the database has 50 trades  
**When** a client sends `GET /api/trades?page=1&page_size=20`  
**Then** the response status is 200  
**And** `items` contains exactly 20 trades  
**And** `total` = 50  
**And** `page` = 1  
**And** `page_size` = 20  
**And** `pages` = 3  
**And** the returned trades are ordered by `entry_datetime DESC, id DESC`

### AC-02: Filtered list (status + direction)

**Given** trades exist with various statuses and directions  
**When** a client sends `GET /api/trades?status=closed&direction=long`  
**Then** the response status is 200  
**And** every trade in `items` has `status="closed"` and `direction="long"`  
**And** `total` reflects only closed long trades  
**And** `pages` is computed correctly for the filtered subset

### AC-03: Search across multiple columns

**Given** trades exist with:
- A trade with `broker_ticket="MT5-12345"`, symbol="EURUSD"
- A trade with `notes_override="manual entry for eurusd"`, symbol="GBPUSD"
- A trade with `broker_ticket="MT5-67890"`, symbol="GBPJPY"

**When** a client sends `GET /api/trades?search=EURUSD`  
**Then** the response status is 200  
**And** the response includes the first two trades (one matched via `asset.symbol`, one via `notes_override`)  
**And** the third trade is NOT included  
**And** the search is case-insensitive (e.g., `search=eurusd` returns the same results)

### AC-04: Sort by whitelist columns

**Given** trades with various `entry_datetime`, `exit_datetime`, `net_pnl`, `symbol`, and `broker_ticket` values  
**When** a client sends `GET /api/trades?sort_by=symbol&sort_dir=asc`  
**Then** the response status is 200  
**And** trades are ordered by `Asset.symbol ASC, id DESC`  
**And** when the client sends `GET /api/trades?sort_by=nonexistent_column`  
**Then** the response status is 422  
**And** the error message indicates invalid `sort_by` value

### AC-05: Summary endpoint with same filter scope

**Given** the trade list returns 15 closed trades and 5 open trades for a given filter set  
**When** a client sends `GET /api/trades/summary?status=closed`  
**Then** the response status is 200  
**And** `total_trades` = 15  
**And** `net_pnl` equals the sum of individual trade PnL for those 15 trades  
**And** `win_rate` = `profitable_count / 15`

**When** the client sends the same filters to `GET /api/trades?page=1&page_size=500`  
**Then** `total` matches `total_trades` from the summary

### AC-06: Pagination correctness

**Given** 45 trades match the current filters and `page_size=20`  
**When** a client requests `page=1`  
**Then** items 1–20 are returned  
**When** requesting `page=2`  
**Then** items 21–40 are returned  
**When** requesting `page=3`  
**Then** items 41–45 are returned  
**When** requesting `page=4`  
**Then** `items` is an empty list  
**And** `total` = 45 (consistent across all pages)  
**And** no trade appears on more than one page  
**And** no trade is skipped

### AC-07: Invalid sort_by rejected

**Given** a client sends `GET /api/trades?sort_by=password_hash`  
**When** the request is processed  
**Then** the response status is 422  
**And** the error detail references the invalid `sort_by` value  
**And** the whitelist of allowed values is included in the error message

When a client sends `GET /api/trades?sort_dir=invalid`  
**Then** the response status is 422 (Pydantic `Literal` validation)

### AC-08: Empty result set

**Given** no trades exist (or filters match zero trades)  
**When** a client sends `GET /api/trades`  
**Then** the response status is 200  
**And** `items` is `[]`  
**And** `total` = 0  
**And** `page` = 1  
**And** `pages` = 1 (minimum 1)

**When** a client sends `GET /api/trades/summary` with the same filters  
**Then** the response status is 200  
**And** `total_trades` = 0  
**And** `net_pnl` = 0.0  
**And** `win_rate` = `null`

### AC-09: Summary rejects pagination/sort params

**Given** a client sends `GET /api/trades/summary?page=3`  
**When** the request is processed  
**Then** the response status is 422  
**And** the error indicates that `page` is not allowed for the summary endpoint  

*(Same for `page_size`, `sort_by`, `sort_dir`.)*

### AC-10: N+1 verification

**Given** the database contains 100 trades across 20 different accounts and 30 different assets  
**When** a client sends `GET /api/trades?page_size=100`  
**Then** the total number of SQL queries executed is exactly **2**: one `COUNT(*)` query and one paginated `SELECT` query with `LEFT OUTER JOIN` on `accounts` and `assets`  
**And** there is NO lazy-load per trade for `account` or `asset` relationships  
**And** the total query count can be asserted in tests via `SQLAlchemy` event listener or `DatabaseQueryCounter` fixture

---

## 5. Performance Requirements

| ID | Requirement | Verification |
|----|-------------|-------------|
| PERF-01 | `TradeRepository.list()` MUST use `joinedload(Trade.account, Trade.asset)` — single query, no N+1 | SQL log assertion in test: exactly 2 statements (count + list) |
| PERF-02 | `TradeRepository.get_summary()` MUST use a single aggregate query — no iteration in Python | SQL log assertion: exactly 1 statement |
| PERF-03 | Zero in-memory filtering, sorting, or pagination — all operations delegated to the database | Code review + SQL log assertion |
| PERF-04 | Search join to `Asset` MUST share the same join when `sort_by=symbol` is also requested (duck join) | SQL log assertion: only 1 JOIN to `assets` |
| PERF-05 | Summary aggregate MUST use SQL `CASE`/`func` expressions, not Python `compute_pnl()` loops | Code review: no `for trade in trades` in `get_summary()` |

### Query count assertion pattern

Tests should use a helper that wraps API calls and counts SQL statements via a session event listener:

```python
# Pseudo-test
async def test_list_query_count(client, db_session, seed_100_trades):
    counter = DatabaseQueryCounter(db_session)
    response = await client.get("/api/trades?page_size=100")
    assert response.status_code == 200
    assert counter.count == 2  # 1 count + 1 list
```

---

## 6. Affected Files

| File | Change Type | Description |
|------|------------|-------------|
| `backend/app/modules/trades/schemas.py` | Modify | Add `sort_by`, `sort_dir` to `TradeFilters`; add `broker_ticket` to `TradeResponse`; add `TradeSummaryResponse` schema |
| `backend/app/modules/trades/repository.py` | Modify | Add `joinedload` for N+1 fix; add sort params; add OR-based search across `broker_ticket`, `asset.symbol`, `notes_override`; add `get_summary()` method |
| `backend/app/modules/trades/service.py` | Modify | Pass sort params to repository; add `get_summary()` method that returns `TradeSummaryResponse` |
| `backend/app/modules/trades/router.py` | Modify | Add `GET /api/trades/summary` route |
| `backend/tests/modules/trades/` | Modify | Update tests for new fields + summary endpoint |
| `frontend/src/modules/trades/` | New | Full module (api, hooks, components, page) |
| `frontend/src/pages/TradingJournal.jsx` | Modify | Delegate to new page component |
| `frontend/src/pages/TradeDetail.jsx` | New | Placeholder page |
| `frontend/src/App.jsx` | Modify | Add `/trades/:id` route |

---

## 7. Open Questions / Clarifications

1. **`net_pnl` sort — computed column in ORDER BY:** Sorting by `net_pnl` requires the computed expression to appear in the ORDER BY clause. SQLAlchemy supports `order_by(case(...))` — verify that this works with the existing query structure and does not cause issues with pagination (SQLite limitation with `OFFSET` in subqueries with complex expressions).
2. **Summary vs. Analytics overlap:** The `GET /api/trades/summary` endpoint is intentionally different from the Analytics module's summary — it filters using the same parameters as the trade list, includes open trades in `total_trades`, and uses a simpler metric set. No deduplication needed.
3. **Search escaping:** The `search` parameter is wrapped in `%...%` and passed to ILIKE. SQL wildcards (`%`, `_`) in user input are interpreted literally by ILIKE. No escaping is needed for user search in this phase.
