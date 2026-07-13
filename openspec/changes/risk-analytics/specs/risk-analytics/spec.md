# Risk Analytics Specification

## Purpose

Risk, exposure, and probabilistic metrics computed in memory from `list_closed()` trades (exposure endpoints use open+closed trades via a single query). Zero schema changes, zero new entities.

---

## Requirements

### Requirement: Risk Metrics — `GET /analytics/risk-metrics`

Single response, all Phase 1 + 4 metrics from one `list_closed()` call.

| Metric | Formula / Source | Null when |
|--------|------------------|-----------|
| Max Consecutive Wins | `compute_streaks().winning_streak.maximum` | 0 trades → 0 |
| Max Consecutive Losses | `compute_streaks().losing_streak.maximum` | 0 trades → 0 |
| Avg Holding Time (hrs) | `avg(exit_dt − entry_dt)` in hours. Exclude open trades, null exit_dt | 0 trades → null |
| Holding Time Dist. | Buckets: `"<1h"`, `"1-4h"`, `"4-24h"`, `"1-7d"`, `">7d"` | 0 trades → `{}` |
| Avg Risk/Trade | `avg(risk_amount)` where `risk_amount > 0` | count of usable = 0 → null |
| Risk Utilization | `avg(risk_amount / abs(entry_price * quantity)) * 100` | 0 usable → null |
| Risk of Ruin | `((1−e)/(1+e))^(C/R)` — see formula below | no balance or R ≤ 0 → null |
| Kelly Fraction | `(p·b − q)/b` where p=wr, q=1−wr, b=avg_win/avg_loss | losses=0 → null; wr≤0 → 0 |
| Expectancy adj. Variance | `expectancy / std(pnl)` | trade_count < 2 → null |

**Risk of Ruin exact formula** (user-specified):
```
edge = win_rate − (1 − win_rate) / profit_factor
RoR  = ((1 − edge) / (1 + edge)) ^ (capital / avg_risk_per_trade)
```

**Kelly disclaimer**: Informative only — NOT an operational recommendation. MUST include disclaimer text in the response body.

**Correlation minimum**: 30 trades per asset pair before computing. Pairs below threshold MUST be excluded (return null for that entry). No correlation computed on small samples.

#### Scenario: Full trade set

- GIVEN 100+ closed trades with risk_amount, balances available
- WHEN `GET /analytics/risk-metrics`
- THEN all 9 metrics populated; Kelly includes `"disclaimer"` field; RoR uses exact formula

#### Scenario: Empty / single / all-wins

| Condition | Behavior |
|-----------|----------|
| 0 closed trades | Consecutive=0, all others null |
| 1 closed trade | Consecutive=1 or 0; holding time = that trade; expect-var = null |
| All wins (gross_loss=0) | profit_factor=null → edge=0 → RoR=((1)/(1))^(C/R)=1; Kelly=null |
| All losses (gross_profit=0) | win_rate=0 → Kelly=0 → not profitable |
| No risk_amount data | avg_risk=null, util=null, RoR=null, Kelly=null |
| No account balance | RoR=null, others computed |

### Requirement: Exposure by Asset — `GET /analytics/exposure/by-asset`

Notional: `sum(position_size × entry_price × direction_sign)`. Sorted by absolute notional descending.

#### Scenario: Assets with notional exposure

- GIVEN 50 trades across 3 assets (AAPL, MSFT, GOOG)
- WHEN `GET /analytics/exposure/by-asset`
- THEN 3 entries `{asset_id, notional: float}`, sorted desc

#### Scenario: Empty or nulls

- GIVEN 0 trades → `[]`
- GIVEN null position_size or entry_price → exclude that trade from sum

### Requirement: Exposure by Session — `GET /analytics/exposure/by-session`

Trade count per market session. Null session_id → `"unknown"`.

#### Scenario: Session distribution

- GIVEN trades in London, NY, Asian sessions
- WHEN `GET /analytics/exposure/by-session`
- THEN each returns `{session_name, trade_count: int}`

#### Scenario: Empty set → `[]`

### Requirement: Exposure by Strategy — `GET /analytics/exposure/by-strategy`

Sum of risk_amount per strategy. Null strategy_id → `"unknown"`.

#### Scenario: Strategy risk totals

- GIVEN 3 strategies with risk_amount populated
- WHEN `GET /analytics/exposure/by-strategy`
- THEN each returns `{strategy_name, risk_total: float}`

#### Scenario: No strategies → `[]`; null risk_amount → counts as 0

### Requirement: Cross-Asset Correlation — `GET /analytics/exposure/correlation`

Pearson correlation of per-trade returns between asset pairs. Min **30 trades per pair** — below threshold → exclude that pair.

#### Scenario: Multi-asset correlation

- GIVEN 3 assets with ≥30 shared trades per pair
- WHEN `GET /analytics/exposure/correlation`
- THEN 3 entries `{asset_a, asset_b, pearson_r, trade_count}`

#### Scenario: Sparse pairs

- GIVEN AAPL×MSFT has 15 shared trades
- THEN AAPL-MSFT excluded (null)

#### Scenario: Single asset or empty → `[]`

### Requirement: Non-functional — Data Access

Every endpoint MUST call trade repository exactly once. `risk-metrics` uses `list_closed()`. Exposure endpoints use a single query covering open+closed trades.

### Requirement: Response Contracts

| Rule | Enforcement |
|------|-------------|
| Empty collections | `[]` — never null |
| Uncomputable metrics | `null` — never 0, never `""`, never missing key |
| Kelly disclaimer | MUST include `disclaimer` field in response |
| Degradation | Partial data → partial response, never 500 |

---

## Edge Cases Matrix

| Condition | Endpoints | Behavior |
|-----------|-----------|----------|
| No closed trades | All | Consecutive=0, rest null / `[]` |
| No trades at all | exposure/* | `[]` |
| Single trade | risk-metrics | Consecutive=1/0, expect-var=null |
| All wins / all losses | risk-metrics (Kelly, RoR) | Kelly=null, RoR=1 or 0 |
| risk_amount all null/0 | avg_risk, util, RoR, Kelly | Those metrics=null |
| No balance | RoR | RoR=null |
| Single asset | correlation | `[]` |
| Null exit_datetime | holding time | Exclude from calc |
| Null market_session_id | by-session | Group under `"unknown"` |
