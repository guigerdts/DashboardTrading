# SDD Spec: Trade Detail & Review MVP

**Change:** `trade-detail-review`
**Phase:** Spec
**Status:** Draft
**Date:** 2026-07-09

---

## Delta for: trade-list (existing)

### MODIFIED Requirements

#### Requirement: Trade list response fields

The `TradeResponse` schema MUST include a `has_review: bool` field indicating whether at least one `TradeReview` exists for that trade.
(Previously: no review status indicator in list response)

The field MUST be computed via a subquery or LEFT JOIN in the repository layer — NOT via per-trade lazy-load.

#### Scenario: Trade with review shows has_review=true

- GIVEN a trade exists
- AND it has at least one `TradeReview` row in `trade_reviews`
- WHEN a client calls `GET /api/trades`
- THEN the response item for that trade has `has_review: true`

#### Scenario: Trade without review shows has_review=false

- GIVEN a trade exists
- AND it has NO `TradeReview` row
- WHEN a client calls `GET /api/trades`
- THEN the response item has `has_review: false`

---

## Full spec for: trade-review (new)

### Purpose

View enriched trade detail, edit a subset of trade fields, and manage post-trade review text (`content` + `lesson_learned`).

### Requirements

#### Requirement: GET /api/trades/{id} — enriched detail

The endpoint MUST return a `TradeDetailResponse` that includes ALL fields from `TradeResponse` PLUS:

| Field | Type | Source |
|-------|------|--------|
| `account_name` | `str` | `Account.name` via joinedload |
| `asset_symbol` | `str` | `Asset.symbol` via joinedload |
| `strategy_id` | `int \| None` | `Trade.strategy_id` |
| `setup_id` | `int \| None` | `Trade.setup_id` |
| `duration_hours` | `float \| None` | Computed: `(exit_datetime - entry_datetime)` in hours, `None` if open |
| `has_review` | `bool` | Subquery: EXISTS in `trade_reviews` |
| `review` | `ReviewResponse \| None` | Embedded review, if any |
| `net_pnl` | `float \| None` | Computed PnL (same formula as summary), `None` if open |
| `return_pct` | `float \| None` | `net_pnl / (entry_price * quantity) * 100`, `None` if open |

##### Scenario: Existing trade returns enriched response

- GIVEN a trade with id=5 exists
- WHEN a client calls `GET /api/trades/5`
- THEN status is 200
- AND `account_name` is populated
- AND `asset_symbol` is populated
- AND `duration_hours` is computed correctly
- AND `net_pnl` matches the summary formula

##### Scenario: Non-existent trade returns 404

- GIVEN no trade with id=999 exists
- WHEN a client calls `GET /api/trades/999`
- THEN status is 404

#### Requirement: Trade review CRUD via sub-resource

The system SHALL expose `GET /api/trades/{id}/review` and `PUT /api/trades/{id}/review`.

`ReviewResponse` schema:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `int` | Review primary key |
| `trade_id` | `int` | FK to trades |
| `content` | `str \| None` | Free-text review |
| `lesson_learned` | `str \| None` | Free-text lesson |
| `created_at` | `str` | Timestamp |
| `updated_at` | `str \| None` | Timestamp |

`ReviewUpdate` schema (for PUT):

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str \| None` | Replaces existing content |
| `lesson_learned` | `str \| None` | Replaces existing lesson |

##### Scenario: GET review returns existing review

- GIVEN trade id=5 has a review with content="Good trade"
- WHEN a client calls `GET /api/trades/5/review`
- THEN status is 200
- AND `content` = "Good trade"

##### Scenario: GET review returns 200 with null fields when no review exists

- GIVEN trade id=5 has NO review
- WHEN a client calls `GET /api/trades/5/review`
- THEN status is 200
- AND `content` is `null`
- AND `lesson_learned` is `null`

##### Scenario: PUT creates review when none exists (upsert)

- GIVEN trade id=5 has NO review
- WHEN a client calls `PUT /api/trades/5/review` with `{"content": "Great trade"}`
- THEN status is 200
- AND a new `TradeReview` row is created
- AND `content` = "Great trade"

##### Scenario: PUT updates existing review

- GIVEN trade id=5 has a review with content="Old"
- WHEN a client calls `PUT /api/trades/5/review` with `{"content": "Updated"}`
- THEN status is 200
- AND `content` = "Updated"

##### Scenario: PUT with null clears review fields

- GIVEN trade id=5 has a review with content="Some text" and lesson_learned="Lesson"
- WHEN a client calls `PUT /api/trades/5/review` with `{"content": null, "lesson_learned": null}`
- THEN status is 200
- AND `content` is `null`
- AND `lesson_learned` is `null`

#### Requirement: Frontend trade detail page

The frontend SHALL provide a page at `/trades/:id` with these blocks:

1. **Trade Header**: symbol, direction, status badge, PnL (colored), broker ticket, account name
2. **Execution Details**: entry price, exit price, quantity, entry datetime, exit datetime
3. **Risk Details**: stop loss, take profit, position size, commission, swap fees
4. **Duration**: computed hours (if closed) or "Open" badge
5. **Review Editor**: textarea for `content`, textarea for `lesson_learned`, save button

##### Scenario: Loading shows skeleton

- GIVEN the user navigates to `/trades/5`
- WHEN the trade detail is loading
- THEN the UI shows skeleton cards
- AND no data blocks are visible

##### Scenario: Error shows ErrorFallback with retry

- GIVEN the API call for trade 5 fails
- WHEN the page renders
- THEN `ErrorFallback` is displayed with error message and retry button
- AND clicking retry re-fetches

##### Scenario: Not-found shows 404 message

- GIVEN the user navigates to `/trades/999`
- AND the API returns 404
- THEN the page shows "Trade not found" with a "Back to Journal" link

##### Scenario: Review save succeeds

- GIVEN the user writes review text and clicks Save
- WHEN the PUT request succeeds
- THEN a success toast or indicator is shown
- AND the review section reflects saved text
