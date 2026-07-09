# Design: Trade Detail & Review MVP

## Technical Approach

Add schemas and routes to the existing trades module (no new backend module). Enrich `GET /api/trades/{id}` with a new `TradeDetailResponse`, add review sub-resource under `/api/trades/{id}/review`. Frontend: new `modules/trade-review/` folder, page at `/trades/:id`, reuse existing shared components. No DB migrations.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Review in trades module vs new module | Inside `modules/trades/` | TradeReview model already exists, no new DI wiring needed. Same pattern as summary endpoint. |
| Review sub-resource vs nested router | Methods on existing `TradeRepository` + `TradeService` | No need for a new router — review is always scoped to a trade. |
| Upsert for review PUT | Single PUT handles create + update | Simpler frontend: one mutation for save, no conditional create-vs-update logic. |
| Detail response vs modifying TradeResponse | New `TradeDetailResponse` | List response stays lean. Detail adds computed fields (duration, PnL) and embedded review. |
| Frontend module under `trades/` vs `trade-review/` | `modules/trade-review/` | Cleaner separation — matches `modules/trading-journal/` and avoids name collision with root `/trades` route. |

## Data Flow

```
Frontend                         Backend
──────────────────────────────────────────────────
GET /trades/:id          →       router.py
  useTradeDetail()       →       service.get_detail(id)
                                   repository.get_with_relations(id)
                                   ← TradeDetailResponse (enriched)

GET /trades/:id/review   →       router.py
  useTradeReview()       →       service.get_review(id)
                                   repository.get_review(id)
                                   ← ReviewResponse (null fields if none)

PUT /trades/:id/review   →       router.py
  useSaveReview()        →       service.upsert_review(id, dto)
                                   repository.upsert_review(id, dto)
                                   ← ReviewResponse
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/modules/trades/schemas.py` | Modify | Add `TradeDetailResponse`, `ReviewResponse`, `ReviewUpdate` schemas; add `has_review` to `TradeResponse` |
| `backend/app/modules/trades/repository.py` | Modify | Add `get_with_relations(id)`, `has_review_subquery()`, `get_review(id)`, `upsert_review(id, dto)` |
| `backend/app/modules/trades/service.py` | Modify | Add `get_detail(id)`, `get_review(id)`, `upsert_review(id, dto)` |
| `backend/app/modules/trades/router.py` | Modify | Add routes for detail, review GET, review PUT; order detail BEFORE `/{id}` |
| `frontend/src/modules/trade-review/api/tradeReviewApi.js` | Create | API service (GET detail, GET review, PUT review) |
| `frontend/src/modules/trade-review/hooks/useTradeDetail.js` | Create | React Query hook for trade detail |
| `frontend/src/modules/trade-review/hooks/useTradeReview.js` | Create | React Query mutation hook for review save |
| `frontend/src/modules/trade-review/components/TradeHeader.jsx` | Create | Symbol, direction, PnL, status badge |
| `frontend/src/modules/trade-review/components/ExecutionDetails.jsx` | Create | Entry/exit, quantity, duration |
| `frontend/src/modules/trade-review/components/RiskDetails.jsx` | Create | SL, TP, position size, commissions |
| `frontend/src/modules/trade-review/components/ReviewEditor.jsx` | Create | Textareas + save button |
| `frontend/src/pages/TradeDetail.jsx` | Create | Page orchestrator (fetch detail + review, render blocks) |
| `frontend/src/App.jsx` | Modify | Add `/trades/:id` route pointing to TradeDetail |
| `frontend/src/modules/trading-journal/components/TradesTable.jsx` | Modify | Add review icon column when `has_review=true` |

## Interfaces / Contracts

```python
# New schemas in schemas.py
class TradeDetailResponse(TradeResponse):
    account_name: str
    asset_symbol: str
    strategy_id: int | None = None
    setup_id: int | None = None
    duration_hours: float | None = None
    net_pnl: float | None = None
    return_pct: float | None = None
    has_review: bool = False
    review: ReviewResponse | None = None

class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    trade_id: int
    content: str | None = None
    lesson_learned: str | None = None
    created_at: str
    updated_at: str | None = None

class ReviewUpdate(BaseModel):
    content: str | None = None
    lesson_learned: str | None = None
```

```js
// Frontend API surface
tradeReviewApi.getDetail(id, { signal })  → TradeDetailResponse
tradeReviewApi.getReview(id, { signal })  → ReviewResponse
tradeReviewApi.saveReview(id, data)        → ReviewResponse
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Backend unit | Repository review methods | Test get_review, upsert_review with real session |
| Backend integration | Detail + review endpoints | FastAPI TestClient, assert enriched fields |
| Frontend | Hook behavior | Mock API, test loading/success/error states |
| Frontend | Component render | Render with fixture data, verify blocks |

## Migration / Rollout

No migration required. TradeReview table already exists. Existing trades have no reviews → `has_review=false`, `review=null`.

## Open Questions

None.
