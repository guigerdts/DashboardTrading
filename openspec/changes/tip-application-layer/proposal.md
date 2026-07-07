# Proposal: TIP Application Layer (MVP)

## Intent

Domain model exists (21 tables, 29 BRs) but zero application-layer code: no repositories, transaction management, BR enforcement, or endpoints — only `NotImplementedError` stubs in 10 module routers. Platform unusable without these layers.

## Scope

**In:** Repository + UoW patterns, Pydantic v2 DTOs, service layer with BR enforcement, full CRUD for Trade/Account/Asset, read-only catalog GET endpoints, integration tests, OpenAPI docs.

**Out:** All other entity endpoints (Strategy, Setup, RiskProfile, TradingSession, Psychology, Review, Tags, Attachment), auth, file upload, reporting, real-time data, schema changes.

## Capabilities

### New
- `trade-crud`: Full CRUD for Trade with BR enforcement
- `account-crud`: Full CRUD for Account with status toggle
- `asset-crud`: Full CRUD for Asset with market filtering
- `catalog-read`: Read-only GET for Market, MarketSession, Timeframe, Broker

### Modified
- None — additive only

## Business Rules (Service-Layer Enforcement)

| BR | Rule | Entity | MVP |
|----|------|--------|:---:|
| BR-07 | SL correct side | Trade | ✓ |
| BR-08 | TP correct side | Trade | ✓ |
| BR-09 | SL/TP opposite | Trade | ✓ |
| BR-10 | Exit pair consistency | Trade | ✓ |
| BR-12 | 30-day soft-lock | Trade | ✓ |
| BR-17 | Broker name ~UNIQUE | Broker | ✓ |
| BR-29 | Soft-delete only (`is_active=False`) | Trade | ✓ |
| BR-21 | Tag non-empty trimmed | Tag | ✗ |
| BR-24 | Attachment ≤ 10MB | Attachment | ✗ |
| BR-28 | Session start ≤ end | TradingSession | ✗ |

## Approach

1. **Repositories** — `AbstractRepository[T]` + `SqlAlchemyRepository[T]` per entity, async `AsyncSession` throughout
2. **Unit of Work** — async context manager exposing all repos as properties, commit/rollback
3. **DTOs** — Pydantic v2 `from_attributes=True`, per-entity Create/Update/Response. `TradeCreate` accepts `open` or `closed` status for historical import.
4. **Services** — receive UoW via DI, enforce BRs at method level. Zero business logic in endpoints.
5. **Endpoints** — extend existing module routers. Trade in `trading_journal`, Account/Asset in dedicated routers, catalogs in shared router or `trading_journal`.

## Delivery — 3 Stacked PRs

| PR | Content | Paths |
|----|---------|-------|
| 1 | Repos + UoW + DTOs | `app/repositories/`, `app/unit_of_work.py`, `app/schemas/` |
| 2 | Services + BRs + unit tests | `app/services/`, BR validation logic |
| 3 | Endpoints + integration tests + OpenAPI | Router mods, `tests/conftest.py`, integration tests |

## Affected Areas

| Area | Impact |
|------|--------|
| `app/repositories/` | New — abstract base + SQLAlchemy implementations |
| `app/unit_of_work.py` | New — async context manager |
| `app/schemas/` | New — Pydantic v2 DTOs |
| `app/services/` | New — BR enforcement layer |
| `app/dependencies.py` | Modified — add UoW DI |
| `app/modules/trading_journal/router.py` | Modified — real endpoints replacing stubs |
| `tests/` | New — integration tests per layer |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing tests use sync engine; new tests need async | Low | Add `pytest-asyncio` fixtures with isolated async SQLite |
| Soft-delete semantics misaligned with `status` | Low | Explicit: `is_active=False` only, `status` unchanged. `'archived'` requires domain model change via new SDD. |
| Seed data dependency in integration tests | Low | Isolated DB per test run — seed via Alembic or inline inserts |

## Rollback

Revert PR commit per stacked PR. All additive code (new files, new endpoints, new schema modules) — zero destructive SQL, no data migration to undo.

## Success Criteria

- [ ] Trade CRUD: create (open/closed), read, soft-delete (`is_active=False`), update within 30-day window
- [ ] Account CRUD: create, read, update, toggle `active`/`inactive`
- [ ] Asset CRUD: create, read, update, search by `symbol` + `market_id` filter
- [ ] Catalogs: read-only GET returning seeded data (Market, MarketSession, Timeframe, Broker)
- [ ] BR-07/08/09/10 enforced in service layer (reject invalid SL/TP/exit combos)
- [ ] BR-12: edits rejected past `editable_until`
- [ ] BR-29: DELETE returns 405 or maps to `is_active=False` — no physical delete
- [ ] Integration tests pass against isolated SQLite (not dev DB)
- [ ] OpenAPI docs (FastAPI auto) render all endpoints
