# Design: Trade Context & Classification

## Technical Approach

Single backend module `trades/catalogs/` with generic CRUD — all 4 entities share one base router/service/repository via parameterization. Pivot tables as separate repository methods on `TradeRepository`. Frontend `modules/catalogs/` for admin pages, extend `modules/trade-review/` for selectors. React Query with explicit cache keys.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Module structure | `app/modules/catalogs/` | Keeps catalog logic separate from trades; follows existing module pattern |
| CRUD reuse | Generic `CatalogService` + `CatalogRepository` parameterized by entity class | Same pattern for all 4 entities — name, description, is_active differ only in shape. Tags add category/color via optional fields |
| Pivot tables | Methods on `TradeRepository` | `trade_tags` and `trade_mistakes` belong to trade context, not catalog CRUD. Avoids circular dependency between modules |
| Loading strategy | `selectinload` for tags/mistakes; `joinedload` for strategy/setup (FKs) | selectinload avoids large cartesian products when a trade has many tags + many mistakes |
| Frontend admin | `modules/catalogs/{entity}/` per entity | Each catalog admin page is self-contained; reuses shared table/form patterns |
| Cache invalidation | Invalidate `['trade', id]` after assignment mutations | Detail page refetches with context. Catalogs lists invalidated after CRUD |

## Data Flow

```
Admin Page                  API                         Trade Detail
─────────                   ───                         ────────────
POST /api/strategies   →   CatalogService.create()
  GET /api/strategies  ←   CatalogService.list()
  GET /api/strategies/{id} ←

                         Trade Detail (from v0.9):
PUT /api/trades/{id}/tags  →   TradeTradeRepository.sync_tags()
  GET /api/trades/{id}    ←   TradeTradeRepository.get_with_context()
                                  ├─ strategy (joinedload)
                                  ├─ setup (joinedload)
                                  ├─ tags (selectinload via pivot)
                                  └─ mistakes (selectinload via pivot)
```

## Query Keys

```
['strategies']              — catalog list
['setups']                  — catalog list
['tags']                    — catalog list
['mistakes']                — catalog list
['trade', id]               — trade detail (includes context)
```

**Invalidation rules:**
- Catalog CRUD → invalidate `['strategies']` / `['setups']` / `['tags']` / `['mistakes']`
- Tag sync → invalidate `['trade', id]`
- Mistake sync → invalidate `['trade', id]`
- PATCH strategy_id/setup_id → invalidate `['trade', id]`

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/strategy.py` | Create | Strategy model (id, name, description, is_active, timestamps) |
| `backend/app/models/setup.py` | Create | Setup model |
| `backend/app/models/tag.py` | Create | Tag model (adds category, color) |
| `backend/app/models/mistake.py` | Create | Mistake model |
| `backend/app/models/__init__.py` | Modify | Export new models |
| `backend/app/db/unit_of_work.py` | Modify | Add catalog repositories + trade context methods |
| `backend/app/modules/catalogs/` | Create | Module with router, schemas, service, repository |
| `backend/app/modules/trades/repository.py` | Modify | Add `sync_tags()`, `sync_mistakes()`, extend `get_with_relations()` for context |
| `backend/app/modules/trades/service.py` | Modify | Add `update_context()`, `sync_tags()`, `sync_mistakes()` |
| `backend/app/modules/trades/schemas.py` | Modify | Add context fields to `TradeDetailResponse` |
| `backend/app/modules/trades/router.py` | Modify | Add tag/mistake sync routes |
| `frontend/src/modules/catalogs/` | Create | Admin pages (list + form) for each entity |
| `frontend/src/modules/trade-review/` | Modify | Replace placeholders with live selectors |
| `frontend/src/pages/TradeDetail.jsx` | Modify | Wire context mutation hooks |
| `frontend/src/App.jsx` | Modify | Add /settings/strategies, /settings/setups, etc. routes |

## Interfaces / Contracts

```python
# Generic catalog schema pattern
class StrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    is_active: bool = True
    created_at: str
    updated_at: str | None = None

# Tag extends with optional fields
class TagResponse(StrategyResponse):
    category: str | None = None
    color: str | None = None
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Backend unit | Catalog CRUD | Test create/read/update/archive per entity |
| Backend unit | Pivot sync | Test replace semantics, duplicate prevention |
| Backend integration | Trade detail context | Assert strategy/setup name, tag list, mistake list all present |
| Backend integration | 409 on duplicate name | POST same name twice → 409 |
| Frontend | Admin pages | Mock API, test list/create/edit/archive flows |
| Frontend | Context assignment | Mock mutation, verify selector behavior |

## Migration / Rollout

New tables only — no migration script needed for existing data. Existing trades get `strategy: null, setup: null, tags: [], mistakes: []` automatically.

## Delivery Estimate

| Component | Est. lines |
|-----------|-----------|
| Backend models (4 files) | ~80 |
| Backend catalogs module | ~250 |
| Backend trades extension | ~120 |
| Backend tests | ~200 |
| Frontend admin pages | ~350 |
| Frontend trade-review extension | ~150 |
| **Total** | **~1,150** |

**Recommendation:** 2 stacked PRs.
- **PR #1** (~450-500): Backend only — models, catalogs module, trades extension, tests
- **PR #2** (~500): Frontend — admin pages, selectors in Trade Detail, routing

## Open Questions

None. Discovery D-01 through D-08 + Spec cover all business rules.
