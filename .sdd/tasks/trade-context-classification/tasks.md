# Tasks: Trade Context & Classification

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,150 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR #1: Backend (~500) → PR #2: Frontend (~500) |
| Delivery strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Work Units

| Unit | Goal | PR |
|------|------|-----|
| 1 | Backend — models, catalogs CRUD, pivots, trades integration, tests | PR #1 (base=main) |
| 2 | Frontend — admin pages, hooks, selectors, tests | PR #2 (base=main) |

---

## Phase 1: Backend models

- [ ] **M1** — Create `models/strategy.py`, `models/setup.py`, `models/tag.py`, `models/mistake.py` with is_active + timestamps; Tag adds category/color
- [ ] **M2** — Export new models from `models/__init__.py`; add catalog repositories to `UnitOfWork`

## Phase 2: Backend catalogs CRUD

- [ ] **C1** — Create `modules/catalogs/schemas.py` (CatalogsResponse, CatalogCreate, CatalogUpdate; TagResponse extends with category/color)
- [ ] **C2** — Create `modules/catalogs/router.py` with generic CRUD route factory (list, get, create, update, archive — same pattern for all 4 entities)
- [ ] **C3** — Create `modules/catalogs/service.py` and `repository.py` with CatalogService/CatalogRepository parameterized by entity class
- [ ] **C4** — Register catalog routes in app

## Phase 3: Backend pivots + trades integration

- [ ] **P1** — Add `sync_tags()`, `sync_mistakes()` to `TradeRepository` (replace semantics; no dups; validate all IDs exist and are active)
- [ ] **P2** — Extend `get_with_relations()` with selectinload for tags/mistakes, joinedload for strategy/setup
- [ ] **P3** — Add `sync_tags()`, `sync_mistakes()`, `update_context()` to `TradeService`; add context fields to `TradeDetailResponse`
- [ ] **P4** — Add PUT `/trades/{id}/tags`, PUT `/trades/{id}/mistakes` to router; extend PATCH `/trades/{id}` for strategy_id/setup_id

## Phase 4: Backend tests

- [ ] **T1** — Test catalog CRUD: create, read, update, archive, duplicate name → 409, archived not in default list
- [ ] **T2** — Test pivot sync: replace semantics, duplicate prevention, archived reference → 422, clear via []
- [ ] **T3** — Test trade detail context: strategy/setup name, tags list, mistakes with note; N+1 assertion

## Phase 5: Frontend admin pages

- [ ] **A1** — Create `modules/catalogs/strategies/`, `setups/`, `tags/`, `mistakes/` pages with shared list + form components
- [ ] **A2** — Create React Query hooks per catalog (`useStrategies`, `useSetups`, `useTags`, `useMistakes`) with CRUD mutations that invalidate `['{entity}']` on success
- [ ] **A3** — Create admin page components (list table with archive action, create/edit modal or inline form)
- [ ] **A4** — Add `/settings/strategies`, `/settings/setups`, `/settings/tags`, `/settings/mistakes` routes to App.jsx

## Phase 6: Frontend context integration

- [ ] **I1** — Create `useTradeContext` mutation hook (sync tags, sync mistakes); invalidates `['trade', id]` on success
- [ ] **I2** — Replace strategy/setup placeholders in TradeDetail with single-select dropdowns (reuse shared Select component)
- [ ] **I3** — Replace tags/mistakes placeholders with multi-select widgets
- [ ] **I4** — Wire context mutations to TradeDetail save flow; verify cache invalidation via React Query DevTools or manual assertion

## Phase 7: Frontend tests

- [ ] **F1** — Test admin list renders catalog elements
- [ ] **F2** — Test create/edit form submits correct payload
- [ ] **F3** — Test archive removes from list
- [ ] **F4** — Test context selectors call correct mutation

## AC Coverage Matrix

| AC | Tasks |
|----|-------|
| AC-01 to AC-04 (CRUD) | C1-C4, T1 |
| AC-05 (archived excluded from list) | T1 |
| AC-06 (archived resolves in detail) | P2, P3, T3 |
| AC-07 (assign archived → 422) | P1, P3, T2 |
| AC-08, AC-09 (sync replaces all) | P1, P3, T2 |
| AC-10 (clear via []) | P1, T2 |
| AC-11 (no duplicate pivots) | P1, T2 |
| AC-12 (null clears assignment) | P3, T3 |
| AC-13 (non-existent ref → 422) | P1, T2 |
| AC-14 (v0.9 regression) | T3 |
| AC-15 (no N+1) | P2, T3 |
