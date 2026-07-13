# Equity & Performance Analytics Specification

## Purpose

Rolling windowed metrics, performance grouped by calendar period, and
date-range comparison — all computed in memory from `list_closed()` trades.
Zero schema changes, zero new entities.

## Requirements

### Requirement: Rolling Windowed Metrics — `GET /analytics/rolling`

Returns sliding-window performance over the N most recent closed trades.

| Param | Type | Required | Default | Validation |
|-------|------|----------|---------|------------|
| `window_size` | `int` | No | `30` | `10`–`200`, else 422 |

`window_size` is additive to `AnalyticsFilter` (`schemas.py`, `buildParams.js`).

Response:

```
{
  window_size: int,
  points: [
    {
      index: int,
      win_rate: float,
      profit_factor: float,
      expectancy: float,
      avg_r_multiple: float,
      trade_count: int
    }
  ]
}
```

When `trade_count < window_size` → `points` MUST be an empty array `[]`.

#### Scenario: Standard rolling window

- GIVEN 100 closed trades
- WHEN `window_size=30`
- THEN 70 points, each computed over the preceding 30 trades, ordered by exit_datetime ASC

#### Scenario: Insufficient trades

- GIVEN 15 closed trades
- WHEN `window_size=30`
- THEN `points` is `[]`, response is 200 with empty array

### Requirement: Performance by Period — `GET /analytics/performance/by-period`

Groups trades by `month | quarter | year`. Each record:

| Field | Type |
|-------|------|
| `period` | `string` |
| `trade_count` | `int` |
| `net_pnl`, `gross_profit`, `gross_loss` | `float` |
| `win_rate`, `profit_factor`, `expectancy`, `avg_r_multiple` | `float` |

Query param: `group_by` — one of `month`, `quarter`, `year`.

#### Scenario: Group by month

- GIVEN trades across Jan–Mar 2026
- WHEN `group_by=month`
- THEN 3 records, one per month, each with full metrics

#### Scenario: Period with no trades

- GIVEN `group_by=year`, no trades in 2024
- THEN response omits 2024 (no empty records for absent periods)

#### Scenario: Zero gross loss in a period

- GIVEN all trades are winners in a period
- THEN `profit_factor` MUST be `null` (division by zero), `gross_loss=0.0`

### Requirement: Compare Periods — `GET /analytics/performance/compare`

Compare two arbitrary date ranges. Frontend MUST NOT calculate deltas.

| Param | Type | Required |
|-------|------|----------|
| `period_a_from`, `period_a_to` | `datetime` | Yes |
| `period_b_from`, `period_b_to` | `datetime` | Yes |

Response:

```
{
  period_a: { … same record as Performance by Period … },
  period_b: { … },
  delta: { same fields, absolute difference },
  delta_percent: { same fields, percentage difference }
}
```

`delta_percent` uses `period_a` as base. If base is `0`, delta_percent for that field is `null`.

#### Scenario: Two date ranges compared

- GIVEN H1 trades and H2 trades
- WHEN comparing H1 vs H2
- THEN both period records include full metrics, delta and delta_percent contain every field

#### Scenario: No trades in one range

- GIVEN `period_a` has 10 trades, `period_b` has 0
- THEN `period_b` returns `trade_count=0`, all metrics `0.0` or `null`; delta_percent is `null` where base is `0`

### Requirement: Edge Cases

| Condition | Behavior |
|-----------|----------|
| Fewer trades than `window_size` | `points: []` (not null) |
| No trades in period | `trade_count: 0`, all metrics `0.0`, `profit_factor: null`, `avg_r_multiple: null` |
| `gross_loss = 0` (all wins) | `profit_factor: null` (undefined — consistent with existing `PerformanceMetrics.profit_factor`) |
| Compare: base is 0 | `delta_percent` field is `null` for that metric |
| Types | Prefer `0`, `[]`, `null` over mixed types — no `None` where `0` is valid |

All sentinel values MUST be documented and consistent with existing `PerformanceMetrics`.

### Requirement: Non-functional — Data Access

Every endpoint MUST call `TradeRepository.list_closed()` exactly once per
request. No N+1 queries, no duplicate fetches. All metrics computed in-memory
from the loaded trade list via pure calculator functions.

#### Scenario: Single list_closed call

- GIVEN any analytics request
- WHEN the service method runs
- THEN `list_closed` is awaited exactly once
