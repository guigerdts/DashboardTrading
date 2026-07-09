# Trading Journal MVP — Implementation Tasks

> **Change**: `trading-journal-mvp`
> **Generated**: 2026-07-09
> **Spec**: Engram #1018 | **Design**: Engram #1019 + 4 refinements (REF-01–REF-04)

---

## Phase 1: Backend (trades module)

---

### Task B1 — Fix N+1 in `TradeRepository.list()` with eager loading

| Field | Value |
|---|---|
| **Files** | `backend/app/modules/trades/repository.py` |
| **Depends on** | — |
| **Complexity** | S |
| **Covers** | AC-01, PERF-01, PERF-02 |

Add `joinedload(Trade.asset)` and `joinedload(Trade.account)` to the paginated query in `TradeRepository.list()`. The `Asset` relationship uses `lazy="raise"` — without eager loading, accessing `trade.asset.symbol` crashes at runtime. This is the foundational fix for `asset_symbol` in responses and for `sort_by=symbol`.

**Implementation notes**:
- Same pattern as `list_closed()` (lines 45–46 in repository.py)
- Apply to the data query only (not the count query — just counting rows)
- Only one join to Asset — reused for `sort_by=symbol` (Task B2) and `search` on `asset.symbol`

---

### Task B2 — Add sort params and stable sort tiebreaker to repository

| Field | Value |
|---|---|
| **Files** | `backend/app/modules/trades/repository.py` |
| **Depends on** | B1 |
| **Complexity** | M |
| **Covers** | REQ-SPEC-02, AC-02, AC-03, PERF-03 |

Add `sort_by: str` and `sort_dir: str` parameters to `TradeRepository.list()`.

**Supported sort keys**:

| `sort_by` | Implementation |
|---|---|
| `entry_datetime` (default) | `Trade.entry_datetime` — native column |
| `exit_datetime` | `Trade.exit_datetime` — native column |
| `symbol` | `Asset.symbol` — requires the join from B1 |
| `pnl` | SQL CASE expression: `(exit_price - entry_price) * quantity * direction_sign - commission - swap_fees` |

**Stable sort tiebreaker** (REQ-SPEC-02): append `Trade.id.desc()` to every ORDER BY clause so pagination boundaries stay deterministic across pages. Without this, trades sharing the same `entry_datetime` could flip between pages.

**`sort_dir`**: `asc` / `desc`. Default `desc` for `entry_datetime`, `asc` for `symbol`.

**`pnl` sort**: compute PnL as a SQL expression in the ORDER BY clause — do NOT sort in Python.

---

### Task B3 — Add `asset_symbol` to `TradeResponse`

| Field | Value |
|---|---|
| **Files** | `backend/app/modules/trades/schemas.py` |
| **Depends on** | B1 (join must exist, or it crashes with `lazy="raise"`) |
| **Complexity** | S |
| **Covers** | AC-04 |

Add `asset_symbol: str` field to `TradeResponse`. During serialization, the ORM model's `trade.asset.symbol` is read via the eagerly-loaded relationship (from Task B1). No custom serializer needed — `from_attributes=True` reads through the relationship.

```python
class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    # ... existing fields ...
    asset_symbol: str  # 👈 new field
    # ...
```

---

### Task B4 — Add summary endpoint: repository layer

| Field | Value |
|---|---|
| **Files** | `backend/app/modules/trades/repository.py` |
| **Depends on** | B1 |
| **Complexity** | L |
| **Covers** | AC-06, AC-07, AC-08, PERF-04, PERF-05 |

New method `TradeRepository.get_summary(filters: dict) -> dict` that returns a single-row aggregation using SQL CASE expressions (NOT Python iteration — PERF-04).

**SQL structure**:

```sql
SELECT
  COUNT(*)                                              AS total_trades,
  SUM(CASE WHEN direction = 'long'
    THEN (exit_price - entry_price) * quantity - commission - swap_fees
    ELSE (entry_price - exit_price) * quantity - commission - swap_fees
  END)                                                  AS total_pnl,
  SUM(CASE WHEN pnl_expr > 0 THEN 1 ELSE 0 END)         AS win_count,
  SUM(CASE WHEN pnl_expr < 0 THEN 1 ELSE 0 END)         AS loss_count,
  AVG(CASE WHEN pnl_expr > 0 THEN pnl_expr END)         AS avg_win,
  AVG(CASE WHEN pnl_expr < 0 THEN pnl_expr END)         AS avg_loss,
  SUM(CASE WHEN pnl_expr > 0 THEN pnl_expr ELSE 0 END)  AS total_win_pnl,
  ABS(SUM(CASE WHEN pnl_expr < 0 THEN pnl_expr ELSE 0 END)) AS total_loss_pnl
FROM trades
  JOIN assets ON trades.asset_id = assets.id
WHERE trades.status = 'closed'
  AND trades.is_active = 1
```

- Use a CTE or subquery to define `pnl_expr` once and reference it in multiple CASE expressions.
- `profit_factor` is computed in Python from `total_win_pnl / total_loss_pnl` (safe — one row). Return `None` when `loss_count = 0` (AC-08).
- `win_rate` = `win_count / total_trades`.
- Filters support the same set as `list()` minus pagination: `status`, `direction`, `account_id`, `asset_id`, `date_from`, `date_to`, `search`, `symbol`.

---

### Task B5 — Add summary endpoint: service layer

| Field | Value |
|---|---|
| **Files** | `backend/app/modules/trades/service.py` |
| **Depends on** | B4 |
| **Complexity** | S |
| **Covers** | — |

New method `TradeService.get_summary(filters: TradeFilters) -> dict`. Thin delegation to `TradeRepository.get_summary()`, extracting filter fields from the `TradeFilters` DTO (same pattern as the existing `list()` method at lines 100–116 of `service.py`).

```python
async def get_summary(self, filters: TradeFilters) -> dict:
    """Return aggregated trade summary for the journal."""
    return await self.uow.trades.get_summary(
        status=filters.status,
        direction=filters.direction,
        account_id=filters.account_id,
        # ... etc
    )
```

---

### Task B6 — Add summary endpoint: router + schemas

| Field | Value |
|---|---|
| **Files** | `backend/app/modules/trades/router.py`, `backend/app/modules/trades/schemas.py` |
| **Depends on** | B2, B5 |
| **Complexity** | M |
| **Covers** | AC-05, AC-09, AC-10 |

**New schema** (`schemas.py`):

```python
class TradeSummaryResponse(BaseModel):
    total_trades: int
    total_pnl: float
    win_count: int
    loss_count: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float | None  # None when loss_count=0
```

**New route** (`router.py`):

```python
@router.get("/summary", response_model=TradeSummaryResponse)
async def get_trades_summary(
    filters: TradeFilters = Depends(),
    svc: TradeService = Depends(get_trade_service),
):
    """Return aggregated trade summary for the journal."""
    return await svc.get_summary(filters)
```

**⚠️ Route ordering is critical**: insert the `/summary` route BEFORE the `/{id}` route (currently at line 58 of `router.py`). FastAPI matches routes in declaration order — `/{id}` would greedily match `summary` as `id="summary"` and return a 404.

Also add `symbol` filter to `TradeFilters`:

```python
class TradeFilters(PaginationParams):
    """Query parameters for filtering the trades list endpoint."""
    # ... existing fields ...
    symbol: str | None = None  # 👈 new — filter by asset symbol
```

---

## Phase 2: Frontend (trading journal module)

---

### Task F1 — Create trades API service ✅

| Field | Value |
|---|---|
| **Files** | `frontend/src/modules/trading-journal/services/tradesApi.js` |
| **Depends on** | B6 (API must exist) |
| **Complexity** | S |
| **Covers** | — |

Follow the exact pattern from `frontend/src/modules/analytics/services/analyticsApi.js`.

```js
import { api } from '../../../shared/lib/api';

function buildParams(filters = {}) {
  const params = {};
  if (filters.search) params.search = filters.search;
  if (filters.status) params.status = filters.status;
  if (filters.direction) params.direction = filters.direction;
  if (filters.symbol) params.symbol = filters.symbol;
  if (filters.sortBy) params.sort_by = filters.sortBy;
  if (filters.sortDir) params.sort_dir = filters.sortDir;
  if (filters.accountId) params.account_id = filters.accountId;
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.page) params.page = filters.page;
  if (filters.pageSize) params.page_size = filters.pageSize;
  return params;
}

export const tradesApi = {
  getTrades: (filters, { signal } = {}) =>
    api.get('/trades', { params: buildParams(filters), signal }),

  getTradesSummary: (filters, { signal } = {}) =>
    api.get('/trades/summary', { params: buildSummaryParams(filters), signal }),
};
```

Pass through `signal` for request cancellation (see Task F9).

---

### Task F2 — Create `useJournalTrades` hook ✅

| Field | Value |
|---|---|
| **Files** | `frontend/src/modules/trading-journal/hooks/useJournalTrades.js` |
| **Depends on** | F1, F3 |
| **Complexity** | M |
| **Covers** | REF-04 (page clamping), REQ-SPEC-01 (page reset) |

React Query hook following `useSummary.js` pattern. Key behaviors:

```js
import { useQuery } from '@tanstack/react-query';
import { useJournalFilters } from './useJournalFilters';
import { tradesApi } from '../services/tradesApi';

function isFiltered(filters) {
  return !!(
    filters.search || filters.status || filters.direction ||
    filters.symbol || filters.accountId ||
    filters.dateFrom || filters.dateTo
  );
}

export function useJournalTrades() {
  const { filters, setFilters } = useJournalFilters();

  const query = useQuery({
    queryKey: ['trades', 'journal', filters],
    queryFn: ({ signal }) => tradesApi.getTrades(filters, { signal }),
  });

  // REF-04: Page clamping — if response.pages < current page, reset to 1
  const prevPagesRef = useRef(null);
  useEffect(() => {
    const pages = query.data?.pages;
    if (pages !== undefined && pages !== null && pages !== prevPagesRef.current) {
      if (filters.page > pages) {
        setFilters({ page: 1 });
      }
      prevPagesRef.current = pages;
    }
  }, [query.data?.pages, filters.page, setFilters]);

  return {
    ...query,
    isEmpty: query.isSuccess && query.data?.total === 0 && !isFiltered(filters),
    isFilteredEmpty: query.isSuccess && query.data?.total === 0 && isFiltered(filters),
  };
}
```

**State machine for consumers**:
| State | `useJournalTrades` property |
|---|---|
| Loading | `isLoading` |
| Error | `isError` |
| Empty (no trades exist) | `isEmpty` |
| Filtered-empty (trades exist, none match) | `isFilteredEmpty` |
| Success with data | `isSuccess && !isEmpty && !isFilteredEmpty` |

---

### Task F3 — Create `useJournalFilters` hook ✅

| Field | Value |
|---|---|
| **Files** | `frontend/src/modules/trading-journal/hooks/useJournalFilters.js` |
| **Depends on** | — |
| **Complexity** | M |
| **Covers** | REF-01 (search debounce 300ms), REQ-SPEC-01 (page reset) |

URL-synced filter state, following the `useDashboardFilters.js` pattern.

**Filter surface**:

| Filter | URL param | Type | Debounce | Resets page? |
|---|---|---|---|---|
| `search` | `search` | string (text) | 300ms | Yes |
| `status` | `status` | string (select) | No | Yes |
| `direction` | `direction` | string (select) | No | Yes |
| `symbol` | `symbol` | string (text) | 300ms | Yes |
| `sortBy` | `sort_by` | string (select) | No | No |
| `sortDir` | `sort_dir` | string (select) | No | No |
| `dateFrom` | `date_from` | date | No | Yes |
| `dateTo` | `date_to` | date | No | Yes |
| `page` | `page` | int | No | — |

**Implementation**:

```js
export function useJournalFilters() {
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(() => ({
    search: searchParams.get('search') || null,
    status: searchParams.get('status') || null,
    direction: searchParams.get('direction') || null,
    symbol: searchParams.get('symbol') || null,
    sortBy: searchParams.get('sort_by') || 'entry_datetime',
    sortDir: searchParams.get('sort_dir') || 'desc',
    dateFrom: searchParams.get('date_from') || null,
    dateTo: searchParams.get('date_to') || null,
    page: parseInt(searchParams.get('page') || '1', 10),
    pageSize: parseInt(searchParams.get('page_size') || '20', 10),
  }), [searchParams]);

  // Debounce refs for search and symbol (text inputs)
  const debounceRefs = useRef({});

  function updateURL(partial) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      const pageResettingFilters = ['search', 'status', 'direction', 'symbol', 'dateFrom', 'dateTo'];

      for (const [key, value] of Object.entries(partial)) {
        if (value != null && value !== '') {
          next.set(key === 'pageSize' ? 'page_size' : key.replace(/[A-Z]/g, m => '_' + m.toLowerCase()), value);
        } else {
          next.delete(key === 'pageSize' ? 'page_size' : key.replace(/[A-Z]/g, m => '_' + m.toLowerCase()));
        }
      }

      // REQ-SPEC-01: reset page to 1 when a filter changes (but not when page itself changes)
      if (!('page' in partial) && pageResettingFilters.some(k => k in partial)) {
        next.set('page', '1');
      }

      return next;
    }, { replace: true });
  }

  const setFilters = useCallback((partial) => {
    // Debounce text inputs (search, symbol)
    const debounceKeys = ['search', 'symbol'];
    const needsDebounce = Object.keys(partial).some(k => debounceKeys.includes(k));

    if (needsDebounce) {
      // Cancel existing debounce for that key
      for (const key of Object.keys(partial)) {
        if (debounceKeys.includes(key)) {
          if (debounceRefs.current[key]) clearTimeout(debounceRefs.current[key]);
          debounceRefs.current[key] = setTimeout(() => updateURL({ [key]: partial[key] }), 300);
        }
      }
    } else {
      // Immediate update for selects, dates, sort, page
      updateURL(partial);
    }
  }, []);

  const clearFilters = useCallback(() => {
    Object.values(debounceRefs.current).forEach(t => clearTimeout(t));
    debounceRefs.current = {};
    setSearchParams({}, { replace: true });
  }, [setSearchParams]);

  const setPage = useCallback((page) => setFilters({ page }), [setFilters]);

  // Cleanup debounce timers on unmount
  useEffect(() => {
    return () => Object.values(debounceRefs.current).forEach(t => clearTimeout(t));
  }, []);

  return { filters, setFilters, clearFilters, setPage };
}
```

---

### Task F4 — Create `TradesTable` component ✅

| Field | Value |
|---|---|
| **Files** | `frontend/src/modules/trading-journal/components/TradesTable.jsx` |
| **Depends on** | F2 |
| **Complexity** | L |
| **Covers** | AC-04, AC-09, REF-03 |

Reusable table component with **5 state machine branches**:

| State | What renders |
|---|---|
| `isLoading` | 8 skeleton rows matching table layout |
| `isError` | `<ErrorFallback message={error.message} onRetry={onRetry} />` |
| `isEmpty` | Full-width message: "No trades yet. Import your first trades to get started." + CTA button linking to `/imports/mt5` |
| `isFilteredEmpty` | Full-width message: "No trades match your filters. Try adjusting your search or filter criteria." + "Clear filters" button |
| `isSuccess` | `<table>` with all trade rows |

**Columns** (configurable via shared column config):

| Column | Content | Sortable |
|---|---|---|
| Symbol | `asset_symbol` | Yes |
| Direction | icon + text (Long↑ / Short↓) | No |
| Entry Date | formatted `entry_datetime` | Yes |
| Exit Date | formatted `exit_datetime` (— for open) | Yes |
| P&L | formatted currency, green/red | Yes |
| Status | badge: Open / Closed | No |

**Props interface**:

```js
{
  data,              // PaginatedResponse from API
  isLoading,         // boolean
  isError,           // boolean
  error,             // Error | null
  onRetry,           // () => void
  isEmpty,           // boolean (from hook)
  isFilteredEmpty,   // boolean (from hook)
  onClearFilters,    // () => void
  onSort,            // (sortBy, sortDir) => void
  sortBy,            // current sort column
  sortDir,           // current sort direction
}
```

---

### Task F5 — Create `JournalFiltersBar` component ✅

| Field | Value |
|---|---|
| **Files** | `frontend/src/modules/trading-journal/components/JournalFiltersBar.jsx` |
| **Depends on** | F3 |
| **Complexity** | M |
| **Covers** | REF-01, AC-01 |

Filter controls bar with:

- **Search input** — placeholder "Search trades...", 300ms debounce via the hook (REF-01)
- **Status dropdown** — All, Open, Closed
- **Direction dropdown** — All, Long, Short
- **Symbol input** — placeholder "Symbol", 300ms debounce via the hook
- **Date from / Date to** — date pickers, immediate update
- **Sort controls** — sort_by dropdown (Entry Date, Exit Date, Symbol, P&L) + sort_dir toggle button (↑ / ↓)
- **"Clear filters"** button — calls `clearFilters`

```js
export function JournalFiltersBar({ onClearFilters }) {
  const { filters, setFilters, clearFilters } = useJournalFilters();

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      {/* Search */}
      <div className="flex flex-col">
        <label className="mb-1 text-xs font-medium text-gray-500">Search</label>
        <input
          type="text"
          value={filters.search || ''}
          onChange={e => setFilters({ search: e.target.value || null })}
          placeholder="Search trades..."
          className="w-48 rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
        />
      </div>

      {/* Status */}
      <div className="flex flex-col">
        <label className="mb-1 text-xs font-medium text-gray-500">Status</label>
        <select
          value={filters.status || ''}
          onChange={e => setFilters({ status: e.target.value || null })}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All</option>
          <option value="open">Open</option>
          <option value="closed">Closed</option>
        </select>
      </div>

      {/* Direction */}
      <div className="flex flex-col">
        <label className="mb-1 text-xs font-medium text-gray-500">Direction</label>
        <select
          value={filters.direction || ''}
          onChange={e => setFilters({ direction: e.target.value || null })}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All</option>
          <option value="long">Long</option>
          <option value="short">Short</option>
        </select>
      </div>

      {/* Symbol */}
      <div className="flex flex-col">
        <label className="mb-1 text-xs font-medium text-gray-500">Symbol</label>
        <input
          type="text"
          value={filters.symbol || ''}
          onChange={e => setFilters({ symbol: e.target.value || null })}
          placeholder="Symbol"
          className="w-28 rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>

      {/* Date from */}
      <div className="flex flex-col">
        <label className="mb-1 text-xs font-medium text-gray-500">From</label>
        <input
          type="date"
          value={filters.dateFrom || ''}
          onChange={e => setFilters({ dateFrom: e.target.value || null })}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>

      {/* Date to */}
      <div className="flex flex-col">
        <label className="mb-1 text-xs font-medium text-gray-500">To</label>
        <input
          type="date"
          value={filters.dateTo || ''}
          onChange={e => setFilters({ dateTo: e.target.value || null })}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>

      {/* Sort */}
      <div className="flex items-end gap-2">
        <div className="flex flex-col">
          <label className="mb-1 text-xs font-medium text-gray-500">Sort</label>
          <select
            value={filters.sortBy}
            onChange={e => setFilters({ sortBy: e.target.value })}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm"
          >
            <option value="entry_datetime">Entry Date</option>
            <option value="exit_datetime">Exit Date</option>
            <option value="symbol">Symbol</option>
            <option value="pnl">P&amp;L</option>
          </select>
        </div>
        <button
          onClick={() => setFilters({ sortDir: filters.sortDir === 'asc' ? 'desc' : 'asc' })}
          className="mb-0.5 rounded border border-gray-300 bg-white px-3 py-1.5 text-sm hover:bg-gray-50"
          title={filters.sortDir === 'asc' ? 'Ascending' : 'Descending'}
        >
          {filters.sortDir === 'asc' ? '↑' : '↓'}
        </button>
      </div>

      {/* Clear */}
      {onClearFilters && (
        <button onClick={onClearFilters} className="rounded border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50">
          Clear
        </button>
      )}
    </div>
  );
}
```

---

### Task F6 — Create `JournalSummaryCards` component ✅

| Field | Value |
|---|---|
| **Files** | `frontend/src/modules/trading-journal/components/JournalSummaryCards.jsx` |
| **Depends on** | F2 (summary data) |
| **Complexity** | S |
| **Covers** | AC-07, AC-08 |

Follow the pattern from `SummaryCards.jsx` in the analytics module.

**Props**: `{ data, isLoading, isError, error, onRetry }`

**States**:
- **Loading**: 4 skeleton cards
- **Error**: `<ErrorFallback>` with retry
- **Empty/no data** (data is null): em dashes for all values
- **Success**: formatted cards

**Cards**:
1. Total Trades (plain number)
2. Net P&L (colored green/red, formatCurrency)
3. Win Rate (formatPercent)
4. Profit Factor (formatRatio, or "—" when null)
5. Avg Win / Avg Loss (formatCurrency, side-by-side)

```js
export function JournalSummaryCards({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return <ErrorFallback message={error?.message || 'Failed to load summary'} onRetry={onRetry} />;
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-5 gap-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="80%" className="mt-2" />
          </div>
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="grid grid-cols-5 gap-4">
        <Card title="Total Trades">—</Card>
        <Card title="Net P&L">—</Card>
        <Card title="Win Rate">—</Card>
        <Card title="Profit Factor">—</Card>
        <Card title="Avg Win / Avg Loss">—</Card>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-5 gap-4">
      <Card title="Total Trades">{data.total_trades}</Card>
      <Card title="Net P&L">
        <span className={data.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}>
          {formatCurrency(data.total_pnl)}
        </span>
      </Card>
      <Card title="Win Rate">{formatPercent(data.win_rate)}</Card>
      <Card title="Profit Factor">
        {data.profit_factor != null ? formatRatio(data.profit_factor) : '—'}
      </Card>
      <Card title="Avg Win / Avg Loss">
        <span className="text-green-600">{formatCurrency(data.avg_win)}</span>
        {' / '}
        <span className="text-red-600">{formatCurrency(data.avg_loss)}</span>
      </Card>
    </div>
  );
}
```

---

### Task F7 — Create `JournalPagination` component ✅

| Field | Value |
|---|---|
| **Files** | `frontend/src/modules/trading-journal/components/JournalPagination.jsx` |
| **Depends on** | — |
| **Complexity** | M |
| **Covers** | REF-04, REQ-SPEC-02 (stable sort ensures deterministic pages) |

```js
export function JournalPagination({ page, pages, total, onPageChange }) {
  if (total === 0) return null;

  return (
    <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3">
      <div className="text-sm text-gray-700">
        Page <span className="font-medium">{page}</span> of{' '}
        <span className="font-medium">{pages}</span> ({total} records)
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="rounded border border-gray-300 bg-white px-3 py-1 text-sm disabled:opacity-50"
        >
          Previous
        </button>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
          className="rounded border border-gray-300 bg-white px-3 py-1 text-sm disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
```

The page clamping logic (REF-04) lives in `useJournalTrades` — this component gracefully handles edge cases by disabling buttons.

---

### Task F8 — Implement `TradingJournal` page orchestrator ✅

| Field | Value |
|---|---|
| **Files** | `frontend/src/pages/TradingJournal.jsx` |
| **Depends on** | F4, F5, F6, F7, F2, F3 |
| **Complexity** | M |
| **Covers** | All AC |

Replace the existing scaffold with the full page:

```jsx
import { ErrorBoundary } from '../shared/components/ErrorBoundary';
import { useJournalFilters } from '../modules/trading-journal/hooks/useJournalFilters';
import { useJournalTrades } from '../modules/trading-journal/hooks/useJournalTrades';
import { JournalFiltersBar } from '../modules/trading-journal/components/JournalFiltersBar';
import { JournalSummaryCards } from '../modules/trading-journal/components/JournalSummaryCards';
import { TradesTable } from '../modules/trading-journal/components/TradesTable';
import { JournalPagination } from '../modules/trading-journal/components/JournalPagination';

export default function TradingJournal() {
  const { filters, setFilters, clearFilters, setPage } = useJournalFilters();
  const trades = useJournalTrades();

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Trading Journal</h1>

      <ErrorBoundary>
        <div className="mb-6">
          <JournalFiltersBar onClearFilters={clearFilters} />
        </div>
      </ErrorBoundary>

      <ErrorBoundary>
        <div className="mb-6">
          <JournalSummaryCards
            data={trades.data}
            isLoading={trades.isLoading}
            isError={trades.isError}
            error={trades.error}
            onRetry={trades.refetch}
          />
        </div>
      </ErrorBoundary>

      <ErrorBoundary>
        <div className="mb-6">
          <TradesTable
            data={trades.data}
            isLoading={trades.isLoading}
            isError={trades.isError}
            error={trades.error}
            onRetry={trades.refetch}
            isEmpty={trades.isEmpty}
            isFilteredEmpty={trades.isFilteredEmpty}
            onClearFilters={clearFilters}
            onSort={(sortBy, sortDir) => setFilters({ sortBy, sortDir })}
            sortBy={filters.sortBy}
            sortDir={filters.sortDir}
          />
        </div>
      </ErrorBoundary>

      <ErrorBoundary>
        <JournalPagination
          page={filters.page}
          pages={trades.data?.pages ?? 1}
          total={trades.data?.total ?? 0}
          onPageChange={setPage}
        />
      </ErrorBoundary>
    </div>
  );
}
```

The route at `/trading-journal` already points here (line 25 in `App.jsx`). No routing changes needed.

---

### Task F9 — Fix `api.get()` for AbortSignal passthrough ✅

| Field | Value |
|---|---|
| **Files** | `frontend/src/shared/lib/api.js` |
| **Depends on** | — |
| **Complexity** | S |
| **Covers** | REF-02 |

The current `api.get()` signature `(endpoint, { params = {} } = {})` destructures only `params` and discards any extra options. React Query's default `queryFn` context provides `{ signal }`, but it's never passed through to `fetch()`.

**Fix** — update `api.get()` to accept and forward extra fetch options:

```js
export const api = {
  get: (endpoint, { params = {}, signal } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value != null && value !== '') query.append(key, value);
    });
    const qs = query.toString();
    return request(qs ? `${endpoint}?${qs}` : endpoint, { signal });
  },
};
```

And update `request()` to spread user-provided options after the headers default:

```diff
 async function request(endpoint, options = {}) {
   const url = `${API_BASE}${endpoint}`;
   const response = await fetch(url, {
     headers: { 'Content-Type': 'application/json' },
+    ...options,
   });
```

**⚠️ Order is important**: spreading `...options` after `headers` means callers can override the content-type header — but for signal-only usage this is safe. If stricter isolation is desired, merge `signal` explicitly:

```js
async function request(endpoint, options = {}) {
  const { signal } = options;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    signal,
  });
```

Either approach works. The key requirement is that `AbortSignal` from React Query reaches `fetch()` so in-flight requests are cancelled when the query key changes.

---

## Dependency Graph

```
   B1 (N+1 fix) ─── B3 (asset_symbol in schema)
       │
       ├── B2 (sort + tiebreaker) ─── B6 (summary router)
       │
       └── B4 (summary repo) ─── B5 (summary service) ──┘
                                                             
   F9 (signal passthrough)  ── independent                   
   F3 (journal filters)     ── independent                   
   F7 (pagination)          ── independent                   
                                                             
   F1 (trades API) ← B6                                     
     └── F2 (useJournalTrades) ← F1, F3                     
         ├── F4 (TradesTable) ← F2                          
         └── F6 (SummaryCards) ← F2                         
                                                             
   F5 (JournalFiltersBar) ← F3                              
   F8 (TradingJournal page) ← F4, F5, F6, F7               
```

**Linearized implementation order**:

1. **B1** → **B2** → **B3** (modify existing GET /api/trades)
2. **B4** → **B5** → **B6** (new GET /api/trades/summary)
3. **F9** (signal passthrough — low risk, do early)
4. **F3** → **F5** (filters)
5. **F7** (pagination — independent)
6. **F1** → **F2** → **F4** → **F6** (data → hooks → components)
7. **F8** (page orchestrator — wires everything)

---

## AC / PERF / REF Coverage Matrix

| ID | Description | Task(s) |
|---|---|---|
| **AC-01** | Filters apply to list + summary | B1, B2, B4, B6 |
| **AC-02** | Sort by entry_datetime, exit_datetime, symbol, pnl | B2 |
| **AC-03** | Stable sort tiebreaker (id DESC) | B2 |
| **AC-04** | asset_symbol in trade response | B1, B3 |
| **AC-05** | Summary route at GET /api/trades/summary | B6 |
| **AC-06** | Summary uses SQL CASE, not Python | B4 |
| **AC-07** | Summary returns total, win/loss, avg, profit_factor | B4, B5, B6 |
| **AC-08** | profit_factor = null when loss_count=0 | B4 |
| **AC-09** | Loading skeleton for table | F4 |
| **AC-10** | Error retry on summary + list failure | F4, F6 |
| **REQ-SPEC-01** | Page resets to 1 when filter changes | F3, F2, F7 |
| **REQ-SPEC-02** | id DESC tiebreaker on all ORDER BY | B2 |
| **PERF-01** | Eager loading prevents N+1 | B1 |
| **PERF-02** | Single join to Asset (shared) | B1, B2 |
| **PERF-03** | PnL sort uses SQL expression, not Python | B2 |
| **PERF-04** | Summary aggregation in SQL, not iteration | B4 |
| **PERF-05** | Summary filters use existing indexes | B4 |
| **REF-01** | Search debounce 300ms | F3, F5 |
| **REF-02** | Request cancellation via AbortSignal | F9 |
| **REF-03** | Filtered-empty vs absolute-empty | F2, F4 |
| **REF-04** | Page clamping: page > pages → set 1 | F2, F7 |

---

## Review Workload Forecast

| Metric | Estimate |
|---|---|
| **Backend changed lines** | ~200–280 (repo: 80, service: 20, schemas: 40, router: 40) |
| **Frontend changed lines** | ~450–600 (api: 30, hooks: 80, components: 350, page: 60) |
| **Total estimated** | ~650–880 lines |
| **400-line budget** | ❌ **Exceeded** — frontend alone exceeds the budget |
| **Chained PRs recommended?** | **YES** — split into 2 PRs: |
| | • **PR 1** (backend only): B1–B6 (~250 lines) |
| | • **PR 2** (frontend): F1–F9 (~500 lines) |
| **Decision needed before apply** | **YES** — 2 items: |
| | 1. Confirm PR split strategy (backend-first → frontend) |
| | 2. Confirm whether to put journal endpoints in `modules/trades` (as specified — using `/api/trades` routes) or move to `modules/trading-journal` |
