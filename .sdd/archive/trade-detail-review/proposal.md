# Proposal: Trade Detail & Review MVP

## Intent

User can view a single trade from the Journal, see enriched trade data, and write/edit post-trade reviews. Closes the loop from "find trade in list" to "analyze that trade."

## Scope

### In Scope
- Backend: enrich `GET /api/trades/{id}`, add `PATCH /api/trades/{id}`, add `GET + PUT /api/trades/{id}/review`
- Frontend: new module `modules/trade-review/` with header blocks + review editor
- Navigation: link from Journal table row to detail page
- No DB migrations (entities already exist)

### Out of Scope
- Tags, attachments/screenshots, mistakes, strategy/setup assignment
- Bulk edit, Dashboard changes, MT5 Import changes, Analytics changes

## Capabilities

### New Capabilities
- `trade-review`: View enriched trade detail, edit editable fields, and manage post-trade review text + lessons learned + metadata

### Modified Capabilities
- `trade-list` (existing): Trade list response gains `has_review` boolean flag to signal review presence from list view

## Approach

Backend: 2 new schemas (`TradeDetailResponse`, `ReviewResponse`), one enriched route, one PATCH route, one review sub-resource. Frontend: page reads `id` from URL params, fetches trade + review concurrently, renders as partitioned blocks. Same patterns as Journal (React Query, URL-driven, Card/Skeleton/ErrorBoundary).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/modules/trades/schemas.py` | Modified | Add `TradeDetailResponse`, `ReviewResponse`, `ReviewUpdate` |
| `backend/app/modules/trades/router.py` | Modified | Add routes for detail, patch, review |
| `backend/app/modules/trades/service.py` | Modified | Add detail + review methods |
| `backend/app/modules/trades/repository.py` | Modified | Add review CRUD methods |
| `frontend/src/modules/trade-review/` | New | Full module (api, hooks, components) |
| `frontend/src/pages/TradeDetail.jsx` | New | Page orchestrator |
| `frontend/src/pages/TradingJournal.jsx` | Modified | Row click → navigate to detail |
| `frontend/src/App.jsx` | Modified | Add `/trades/:id` route |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Route `/trades/review` vs `/trades/{id}` ordering | Low | Register detail route before `/{id}` (same pattern as summary) |
| Trade model changes in schema only, no migration | Low | No DB schema changes |

## Rollback Plan

Revert the PATCH/PUT routes if editing causes issues — detail view is read-only safe. Frontend can be rolled back independently.

## Dependencies

- Existing Trade and Review (or Review-like) models in DB

## Success Criteria

- [ ] Trade detail page loads with all trade info from `GET /api/trades/{id}`
- [ ] User can edit and save review text
- [ ] Journal table shows a visual indicator for trades with reviews
- [ ] All existing Journal + backend tests still pass
