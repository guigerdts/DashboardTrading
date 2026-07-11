# Spec: Analytics Dashboard v1.1.0

**Change**: `analytics-dashboard-v1`
**Status**: Draft
**Domain**: Analytics — read-only aggregation and breakdown endpoints

---

## 1. Backward Compatibility Statement

`GET /analytics/summary` is **extended only** — no existing field is renamed, deleted, or changed type:

- Existing fields: `total_trades`, `performance { net_pnl, gross_profit, gross_loss, win_rate, profit_factor, expectancy, avg_win, avg_loss, avg_r_multiple }`, `risk { max_drawdown, max_drawdown_pct, current_drawdown, current_drawdown_pct, recovery_factor, payoff_ratio }`
- Added: `total_trades_all` (sum of open + closed trades matching filters), `total_open_trades` (open trade count matching filters)
- Any client consuming the current shape continues to work — unknown fields are ignored by consumers

---

## 2. API Contracts

### 2.1 Common Filter Parameters

All endpoints accept these optional query parameters:

| Param | Type | Description |
|-------|------|-------------|
| `account_id` | int | Filter by account |
| `asset_id` | int | Filter by asset |
| `market_id` | int | Filter by market |
| `date_from` | datetime (ISO 8601) | Inclusive start of exit date range |
| `date_to` | datetime (ISO 8601) | Inclusive end of exit date range |

### 2.2 Common Breakdown Contract

All four breakdown endpoints (`/strategies`, `/setups`, `/tags`, `/mistakes`) return an **identical structure** per item, enabling a single reusable frontend component:

```json
{
  "id": 1,
  "name": "Breakout",
  "trade_count": 42,
  "win_rate": 63.2,
  "net_pnl": 1845.30,
  "profit_factor": 1.87,
  "expectancy": 43.9
}
```

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | int | No | Entity primary key |
| `name` | string | No | Entity name |
| `trade_count` | int | No | Number of closed trades for this entity |
| `win_rate` | float | No | Win rate (0–100) |
| `net_pnl` | float | No | Sum of net P&L for trades in this group |
| `profit_factor` | float? | Yes | Gross profit / |gross loss|; null when no loss trades |
| `expectancy` | float | No | Average P&L per trade |

### 2.3 GET /analytics/summary — Extended

**Response 200:**

```json
{
  "total_trades": 184,
  "total_trades_all": 200,
  "total_open_trades": 16,
  "performance": {
    "net_pnl": 8450.30,
    "gross_profit": 12450.00,
    "gross_loss": -3999.70,
    "win_rate": 62.5,
    "profit_factor": 3.11,
    "expectancy": 45.93,
    "avg_win": 108.26,
    "avg_loss": -57.97,
    "avg_r_multiple": 1.42
  },
  "risk": {
    "max_drawdown": -2500.00,
    "max_drawdown_pct": -12.3,
    "current_drawdown": -500.00,
    "current_drawdown_pct": -2.8,
    "recovery_factor": 3.38,
    "payoff_ratio": 1.87
  }
}
```

**Response 404 (no trades):**

```json
{ "detail": "No trades match the given filters" }
```

### 2.4 GET /analytics/breakdown/strategies

**Response 200:**

```json
{
  "items": [
    { "id": 1, "name": "Trend Following", "trade_count": 42, "win_rate": 64.3, "net_pnl": 3200.50, "profit_factor": 2.15, "expectancy": 76.20 }
  ]
}
```

- Excludes archived strategies (where `is_active = 0`)
- Includes strategies with zero trades when `include_empty=true` query param is set
- Filtered by common filter params

### 2.5 GET /analytics/breakdown/setups

**Response 200:**

```json
{
  "items": [
    { "id": 1, "name": "Pin Bar", "trade_count": 28, "win_rate": 71.4, "net_pnl": 1850.00, "profit_factor": 2.89, "expectancy": 66.07 }
  ]
}
```

- Excludes archived setups
- Same contract as strategies

### 2.6 GET /analytics/breakdown/tags

**Response 200:** Common breakdown items array.

- Aggregation via `trade_tags` pivot join — `GROUP BY tag_id`
- Only tags with at least one matching trade are returned (no zero rows)
- Tags are joined through the M:N pivot; no dedicated tag-level filtering needed

### 2.7 GET /analytics/breakdown/mistakes

**Response 200:** Common breakdown items array.

- Aggregation via `mistake_entries` pivot join — `GROUP BY mistake_id`
- A trade with multiple mistakes contributes to each mistake's count
- Only mistakes with at least one matching trade are returned

### 2.8 GET /analytics/distribution/r

Returns R-multiple distribution buckets for closed trades.

**Query params**: Common filters + optional `bucket_count` (default: 5) to control bucket granularity.

**Response 200:**

```json
{
  "buckets": [
    { "label": "< -3R", "count": 2, "total_pnl": -6800.00 },
    { "label": "-3R to -1R", "count": 8, "total_pnl": -4200.00 },
    { "label": "-1R to +1R", "count": 95, "total_pnl": 1200.00 },
    { "label": "+1R to +3R", "count": 45, "total_pnl": 22400.00 },
    { "label": "> +3R", "count": 12, "total_pnl": 18000.00 }
  ],
  "total": 162,
  "trades_without_risk": 22
}
```

| Field | Type | Description |
|-------|------|-------------|
| `buckets[].label` | string | Bucket range label |
| `buckets[].count` | int | Number of trades in this bucket |
| `buckets[].total_pnl` | float | Sum of net P&L for trades in this bucket |
| `total` | int | Number of closed trades with `risk_amount` set |
| `trades_without_risk` | int | Number of closed trades without `risk_amount` (excluded from buckets) |

- Only closed trades with a non-null `risk_amount` are bucketed
- R-multiple = `net_pnl / risk_amount`
- Trades without `risk_amount` are counted in `trades_without_risk` but excluded from bucket distribution

### 2.9 GET /analytics/heatmap

Returns a 2D aggregation matrix for visual heatmap rendering.

**Query params**: Common filters + optional `x_axis` (default: `day_of_week`), `y_axis` (default: `hour_of_day`), `metric` (default: `trade_count`, options: `trade_count`, `net_pnl`, `win_rate`).

**Response 200:**

```json
{
  "x_labels": ["Mon", "Tue", "Wed", "Thu", "Fri"],
  "y_labels": ["00:00", "01:00", ..., "23:00"],
  "cells": [
    { "x": 0, "y": 0, "value": 5 },
    { "x": 0, "y": 1, "value": 2 }
  ],
  "metric": "trade_count"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `x_labels` | string[] | Labels for the X axis |
| `y_labels` | string[] | Labels for the Y axis |
| `cells` | Cell[] | Non-empty cells with coordinates and value |
| `metric` | string | The metric used for cell values |

Each cell:

| Field | Type | Description |
|-------|------|-------------|
| `x` | int | Index into `x_labels` |
| `y` | int | Index into `y_labels` |
| `value` | float | Aggregated metric value |

- Trades aggregated by entry datetime dimensions
- Empty cells are omitted (no zero-fill — frontend renders missing cells as blank)
- Default axis: day of week vs hour of day; `x_axis` and `y_axis` query params MAY specify other dimensions (e.g., `month`, `strategy_id`)

---

## 3. Acceptance Criteria

### Summary Endpoint (AC-01–AC-04)

- **AC-01**: `GET /analytics/summary` returns `total_trades`, `total_trades_all`, and `total_open_trades` where `total_trades_all >= total_trades` and `total_open_trades = total_trades_all - total_trades`.
- **AC-02**: When no closed trades match filters but open trades exist, `total_trades = 0`, `total_open_trades > 0`, and `performance` metrics default to zero/null.
- **AC-03**: When no trades at all match filters, returns **404** with `"No trades match the given filters"`.
- **AC-04**: Existing response shape is preserved — any client consuming the pre-1.1.0 response continues to parse correctly.

### Breakdown Endpoints (AC-05–AC-12)

- **AC-05**: `GET /analytics/breakdown/strategies` returns the exact common breakdown contract for each item.
- **AC-06**: `GET /analytics/breakdown/setups` returns the exact common breakdown contract.
- **AC-07**: `GET /analytics/breakdown/tags` returns items aggregated via the `trade_tags` pivot with correct trade counts.
- **AC-08**: `GET /analytics/breakdown/mistakes` returns items aggregated via `mistake_entries` with correct trade counts (a single trade may count toward multiple mistakes).
- **AC-09**: Archived strategies/setups (is_active=0) are excluded from breakdown results by default.
- **AC-10**: A strategy with zero matching trades is excluded unless `include_empty=true` is set.
- **AC-11**: Breakdown items are sorted by `trade_count DESC` then `name ASC`.
- **AC-12**: When filters return no trades for any entity, all breakdown endpoints return `{ "items": [] }`.

### Distribution Endpoint (AC-13–AC-15)

- **AC-13**: `GET /analytics/distribution/r` returns buckets where each trade is in exactly one bucket, or in `trades_without_risk` if `risk_amount` is null.
- **AC-14**: Bucket labels are evenly split across the observed range of R-multiple values; `bucket_count` param controls granularity.
- **AC-15**: When no closed trades have `risk_amount`, returns `{ "buckets": [], "total": 0, "trades_without_risk": <count> }`.

### Heatmap Endpoint (AC-16–AC-18)

- **AC-16**: `GET /analytics/heatmap` returns cells with valid `x`, `y` indices into the corresponding label arrays.
- **AC-17**: Empty cells are omitted from the response (no zero-fill).
- **AC-18**: `metric` param changes the cell value aggregation (`net_pnl`, `win_rate`, `trade_count`).

### Performance & Filters (AC-19–AC-20)

- **AC-19**: Every endpoint executes exactly **one SQL query** (one `SELECT` statement) — no N+1, no subsequent Python-side aggregation.
- **AC-20**: Invalid filter values (e.g., `account_id=abc`, `date_from=not-a-date`) return **422 Unprocessable Entity** with validation error details.

---

## 4. Use Cases

| ID | User Story |
|----|-----------|
| UC-01 | As a trader, I want to see my **overall performance summary** (total trades, net P&L, win rate, profit factor, max drawdown) so I can assess my trading at a glance. |
| UC-02 | As a trader, I want to see **performance broken down by strategy** to identify which strategies are profitable and which need adjustment. |
| UC-03 | As a trader, I want to see **performance broken down by setup pattern** (e.g., Pin Bar, Engulfing) to evaluate entry/exit pattern effectiveness. |
| UC-04 | As a trader, I want to see **performance broken down by tag** to analyze custom categories I've assigned to trades. |
| UC-05 | As a trader, I want to see **performance broken down by mistake type** so I can identify my most costly behavioral errors. |
| UC-06 | As a trader, I want to see the **distribution of my R-multiple values** to understand my risk/reward profile and whether my edge is consistent. |
| UC-07 | As a trader, I want to see a **trading heatmap** (e.g., P&L by day of week and hour) to identify my most and least profitable trading times. |
| UC-08 | As a trader, I want to **filter all analytics by date range, account, asset, or market** so I can analyze specific periods or instruments. |

---

## 5. Performance Requirements

- **Single SQL query per endpoint**: Each endpoint MUST execute exactly one aggregate `SELECT` statement. No in-memory aggregation loops over fetched trade lists.
- **No N+1**: Category lookups (strategy/setup/tag/mistake names) MUST be resolved in the same query via JOINs or subqueries — not fetched per row.
- **SQL-native aggregation**: All `COUNT`, `SUM`, `AVG`, `CASE` expressions are pushed to the database. Python/numpy aggregation over fetched rows is NOT acceptable for breakdown endpoints.
- **No pagination**: Breakdowns return all catalog items. Trade lists are already paginated in the trades module — no pagination needed in analytics.
- **No new indexes or migrations**: Existing indexes (`ix_trades_strategy_id`, `ix_trades_setup_id`, `ix_trade_tags_tag_id`, `ix_mistake_entries_mistake_id`, among others) are sufficient for the expected trade volumes (O(10k)).
- **M:N pivot handling** (tags, mistakes): Subqueries or `GROUP BY` on the pivot join — no fetching all pivot rows into memory.
- **Expected performance**: Sub-200ms response for up to 10k closed trades with all filters applied.

---

## 6. Cache Strategy

### React Query Cache Keys

All analytics endpoints are **GET-only, read-only** — no mutations invalidate them. Stale data is acceptable within the staleness window.

```typescript
// Cache key factories (parameterized by current filters)
['analytics', 'summary', filters]
['analytics', 'breakdown', 'strategies', filters]
['analytics', 'breakdown', 'setups', filters]
['analytics', 'breakdown', 'tags', filters]
['analytics', 'breakdown', 'mistakes', filters]
['analytics', 'distribution', 'r', filters]
['analytics', 'heatmap', filters]
```

### Staleness Guidance

| Endpoint | Suggested `staleTime` | Rationale |
|----------|----------------------|-----------|
| Summary | 30s | KPIs may update as trades close intraday |
| Breakdowns | 60s | Less frequent changes — catalogs are static |
| Distribution R | 60s | R-multiple distribution shifts slowly |
| Heatmap | 120s | Time-based heatmap changes only with new trades |

No `refetchInterval` needed — filters changes via `useDashboardFilters()` drive automatic refetch through the query key dependency.

---

## 7. Error Codes

| Status | Condition | Body |
|--------|-----------|------|
| 200 | Success | Response payload |
| 404 | No trades match the given filters | `{ "detail": "No trades match the given filters" }` |
| 422 | Invalid filter parameter value | Standard FastAPI validation error shape |
| 422 | Invalid `metric`, `x_axis`, or `y_axis` value (heatmap) | `{ "detail": [{ "loc": [...], "msg": "...", "type": "value_error" }] }` |
| 422 | Invalid `bucket_count` (distribution) — must be int ≥ 2 | Same 422 shape |

- 404 is returned when *zero trades* (open + closed) match the filter criteria.
- 422 follows FastAPI default `RequestValidationError` format.
- No 500 errors from the analytics endpoints under normal conditions — malformed queries return 422.
