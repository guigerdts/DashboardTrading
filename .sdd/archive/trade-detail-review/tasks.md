# Tasks: Trade Detail & Review MVP

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~530 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes (stacked: backend-first) |
| Suggested split | PR #1: Backend (R1-R4) → PR #2: Frontend (F1-F9) |
| Delivery strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

## Phase 1: Foundation (schemas + repository)

- [ ] **R1** — Add `ReviewResponse`, `ReviewUpdate`, `TradeDetailResponse` schemas to `schemas.py`; add `has_review: bool` to `TradeResponse` (default `False`)
- [ ] **R2** — Add `get_with_relations(id)`, `get_review(id)`, `upsert_review(id, dto)` to `repository.py`; add `has_review` subquery to `list()` query
- [ ] **R3** — Add `get_detail(id)`, `get_review(id)`, `upsert_review(id, dto)` to `service.py`

## Phase 2: Routes

- [ ] **R4** — Add detail + review routes to `router.py`; ensure detail route registered before `/{id}` catch-all

## Phase 3: Frontend API + hooks

- [ ] **F1** — Create `modules/trade-review/api/tradeReviewApi.js` (getDetail, getReview, saveReview)
- [ ] **F2** — Create `hooks/useTradeDetail.js` (React Query, loading/error/success/not-found states)
- [ ] **F3** — Create `hooks/useTradeReview.js` (React Query mutation, invalidate detail on success)

## Phase 4: Frontend components

- [ ] **F4** — Create `TradeHeader.jsx` (symbol, direction, status badge, PnL, broker ticket, account name)
- [ ] **F5** — Create `ExecutionDetails.jsx` (entry/exit price, quantity, datetime, duration)
- [ ] **F6** — Create `RiskDetails.jsx` (SL, TP, position size, commission, swap fees)
- [ ] **F7** — Create `ReviewEditor.jsx` (content + lesson_learned textareas, save button, loading/error states)

## Phase 5: Page + routing

- [ ] **F8** — Create `pages/TradeDetail.jsx` (orchestrator: fetch detail + review, render blocks, 404 state)
- [ ] **F9** — Add `/trades/:id` route to `App.jsx`; add review icon column to `TradesTable.jsx`

## AC / REQ Coverage Matrix

| ID | Scenario | Task(s) |
|----|----------|---------|
| AC-01 | Existing trade returns enriched response | R1, R2, R3, R4 |
| AC-02 | Non-existent trade returns 404 | R4 |
| AC-03 | GET review with existing review | R2, R3, R4 |
| AC-04 | GET review with no review (null fields) | R2, R3, R4 |
| AC-05 | PUT creates review (upsert) | R2, R3, R4 |
| AC-06 | PUT updates review | R2, R3, R4 |
| AC-07 | PUT with null clears fields | R2, R3, R4 |
| AC-08 | Loading state shows skeletons | F2, F4-F8 |
| AC-09 | Error shows ErrorFallback with retry | F2, F4-F8 |
| AC-10 | 404 shows "Trade not found" | F2, F8 |
| AC-11 | Review save succeeds with indicator | F3, F7 |
| AC-12 | has_review flag in list response | R1, R2 |
