# Tasks: TIP Application Layer (MVP)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,930 total across 6 PRs |
| 400-line budget risk | High — Trades module may reach ~500 lines |
| Chained PRs recommended | Yes |
| Suggested split | Foundation → Catalogs → Trades → Accounts → Assets → Integration |
| Delivery strategy | auto-chain (force-chained) |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

> **Trades size note**: Estimated ~500 lines due to BR complexity (6 BRs, 14 service tests, 12 endpoint tests, full CRUD + close). If this exceeds the 400-line review budget, the service tests (~150 lines) can be split into a separate child PR within the trades concern — but the user's "one task = one module" rule means it should stay as one PR with a `size:exception` note.

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| Foundation | Exceptions, UoW, DI, base repo, pagination, conftest, exception handler in main.py | PR 1 | Base = main; no endpoints yet |
| Catalogs | Catalog module: Market, MarketSession, Timeframe, Broker read + broker CRUD | PR 2 | Base = main; first live endpoints |
| Trades | Trade module: full CRUD + close with BR enforcement | PR 3 | Base = main; largest module |
| Accounts | Account module: full CRUD with name uniqueness | PR 4 | Base = main; independent of Trades |
| Assets | Asset module: full CRUD with symbol+market uniqueness | PR 5 | Base = main; independent of Trades/Accounts |
| Integration | Full-suite verification, end-to-end smoke test | PR 6 | Base = main; final wiring |

---

## Task 1: Foundation ✅

### Files
| File | Action | Description |
|------|--------|-------------|
| `app/core/__init__.py` | ✅ Created | Package init for core/ |
| `app/core/exceptions.py` | ✅ Created | `AppError`, `NotFoundError` (404), `ConflictError` (409), `BusinessRuleError` (422) |
| `app/db/__init__.py` | ✅ Created | Package init for db/ |
| `app/db/unit_of_work.py` | ✅ Created | `UnitOfWork` with lazy-init repo properties using late imports |
| `app/db/dependencies.py` | ✅ Created | `get_db()`, `get_uow()` FastAPI Depends generators; plus service providers `get_trade_service`, `get_account_service`, `get_asset_service`, `get_broker_service` (all using late imports to defer module package resolution); `get_db()` wraps existing `app.database.async_session_factory` |
| `app/modules/shared/__init__.py` | ✅ Created | Package init for shared/ |
| `app/modules/shared/base.py` | ✅ Created | `AbstractRepository[T]` ABC, `SqlAlchemyRepository[T]` with async CRUD |
| `app/modules/shared/pagination.py` | ✅ Created | `PaginationParams`, `PaginatedResponse[T]`, `MessageResponse` |
| `tests/conftest.py` | ✅ Created | Async fixtures: `event_loop` (session), `async_engine` (in-memory SQLite), `db_session` (per-test), `client` (FastAPI test client with overridden DB), `uow` — used by ALL module tests |
| `app/main.py` | ✅ Modified | Add `@app.exception_handler(AppError)` inside `create_app()` to render 404/409/422 responses |

### Dependencies
- None (root task)

### Business Rules
- None (infrastructure — no BR enforcement)

### Foundation Quality Criteria (QC-01 through QC-04)
- **QC-01**: ✅ `SqlAlchemyRepository` never calls `commit()`, `rollback()`, or `close()` — only `flush()` inside `add()` to get generated IDs
- **QC-02**: ✅ Repository files import only `AsyncSession` + domain models — zero FastAPI imports (`fastapi`, `Depends`, `Request`, `Response` not allowed)
- **QC-03**: ✅ Service provider functions are pure construction — `get_trade_service(uow)` returns `TradeService(uow)` with zero business logic
- **QC-04**: ✅ `get_db()` yields one session; `get_uow()` wraps it; all repos in the same UoW share the same `self._session`

### Acceptance Criteria
- [x] `app/core/exceptions.py` defines 4 error classes: `AppError`, `NotFoundError`, `ConflictError`, `BusinessRuleError`, each with correct `.status_code` and `.message`
- [x] `app/modules/shared/base.py` defines `AbstractRepository[T]` with async `add`, `get`, `list`, `update`, `delete`, `exists` methods and `SqlAlchemyRepository[T]` implementation using `AsyncSession` with `flush()` after `add`
- [x] `app/db/unit_of_work.py` defines `UnitOfWork` with lazy-init `.trades`, `.accounts`, `.assets`, `.markets`, `.market_sessions`, `.timeframes`, `.brokers` properties (using late imports to avoid circular dependency before module repos exist)
- [x] `app/db/dependencies.py` defines `get_db()` (wrapping `app.database.async_session_factory`), `get_uow()` (commit on success, rollback on exception), and service providers `get_trade_service`, `get_account_service`, `get_asset_service`, `get_broker_service` (all with late imports)
- [x] QC-01: `SqlAlchemyRepository.add()` does `flush()` but NEVER `commit()` or `rollback()`
- [x] QC-02: No `fastapi`, `Depends`, `Request`, `Response` imports in `app/modules/shared/base.py` or any future repository file
- [x] QC-03: Each provider function body is `from ... import Service; return Service(uow)` — zero business logic
- [x] QC-03: Each provider uses string annotation (`-> "TradeService"`) to avoid eager import resolution
- [x] QC-04: `get_db()` creates one session; `get_uow()` receives it; all UoW repo properties use `self._session`
- [x] `app/modules/shared/pagination.py` defines `PaginationParams` (page/page_size with validation), `PaginatedResponse[T]` (items/total/page/page_size/pages), `MessageResponse`
- [x] `app/main.py` registers global `app_error_handler` that renders `BusinessRuleError` as 422 Pydantic-style array and other `AppError` as `{"detail": "..."}`
- [x] `tests/conftest.py` provides all 5 fixtures; engine uses `sqlite+aiosqlite://` (in-memory), session rolls back after each test

### Required Tests
| File | Tests | Coverage |
|------|-------|----------|
| `tests/conftest.py` | ✅ 5 fixtures | Fixture infrastructure |
| `tests/test_foundation_di.py` | ✅ 6/6 passing | **QC-01**: repo add does NOT commit (flush-only); **QC-04**: shared session across repos; **QC-04**: single session per request via `get_uow()`; auto-commit on success; auto-rollback on exception; `dependency_overrides` works with providers |

### Line Estimate
~380 lines (exceptions: 45, UoW: 55, dependencies: 65, base repo: 70, pagination: 30, conftest: 65, foundation tests: 30, main.py modify: +15, __init__.py files: 15) — ✅ All 37 tests pass (6 foundation + 31 existing)

---

## Task 2: Catalogs ✅

### Files
| File | Action | Description |
|------|--------|-------------|
| `app/modules/catalogs/__init__.py` | ✅ Created | Package init |
| `app/modules/catalogs/repository.py` | ✅ Created | `MarketRepository`, `MarketSessionRepository`, `TimeframeRepository`, `BrokerRepository` — all extending `SqlAlchemyRepository`, with `list_all()` + `get()` + `BrokerRepository.get_by_name()` |
| `app/modules/catalogs/service.py` | ✅ Created | `CatalogService` (list_markets, list_market_sessions, list_timeframes), `BrokerService` (create with BR-17 warning, get, list_all) |
| `app/modules/catalogs/schemas.py` | ✅ Created | `MarketResponse`, `MarketSessionResponse`, `TimeframeResponse`, `BrokerCreate`, `BrokerResponse` — all `from_attributes=True` |
| `app/modules/catalogs/router.py` | ✅ Created | 6 endpoints via `Depends(get_broker_service)`/`get_uow` providers: GET `/api/markets`, `/api/market-sessions`, `/api/timeframes`, `/api/brokers`, GET `/api/brokers/{id}`, POST `/api/brokers` |
| `tests/modules/catalogs/__init__.py` | ✅ Created | Package init |
| `tests/modules/catalogs/test_repository.py` | ✅ Created | 8 tests: `list_all` + `get` for each catalog entity |
| `tests/modules/catalogs/test_endpoints.py` | ✅ Created | 8 tests: GET markets/market-sessions/timeframes/brokers return 200, broker CRUD, 404 for missing broker |

### Dependencies
- Task 1: Foundation

### Business Rules
- **BR-17**: Broker name SHOULD be unique — `BrokerService.create()` logs warning if duplicate, allows creation

### Acceptance Criteria
- [x] GET `/api/markets` returns 200 with `list[MarketResponse]`
- [x] GET `/api/market-sessions` returns 200 with `list[MarketSessionResponse]`
- [x] GET `/api/timeframes` returns 200 with `list[TimeframeResponse]`
- [x] GET `/api/brokers` returns 200 with `list[BrokerResponse]`
- [x] GET `/api/brokers/{id}` returns 200 for existing, 404 for missing
- [x] POST `/api/brokers` creates broker and returns 201 with `BrokerResponse`; duplicate name succeeds with log warning (BR-17)
- [x] Router is auto-discovered by `discover_modules()` — no manual registration

### Required Tests
| File | Tests | Coverage |
|------|-------|----------|
| `tests/modules/catalogs/test_repository.py` | ✅ 8/8 passing | `list_all` + `get` for Market, MarketSession, Timeframe, Broker |
| `tests/modules/catalogs/test_endpoints.py` | ✅ 8/8 passing | Read-only GET (4), broker GET (1), broker create (2), broker not-found (1) |

### Line Estimate
~335 lines

---

## Task 3: Trades

### Files
| File | Action | Description |
|------|--------|-------------|
| `app/modules/trades/__init__.py` | Create | Package init |
| `app/modules/trades/repository.py` | Create | `TradeRepository` with filtered `list()` (status, direction, account_id, asset_id, date_from, date_to, search, is_active) + pagination + entry_datetime DESC ordering |
| `app/modules/trades/service.py` | Create | `TradeService` with `create` (BR-07/08/09/10), `get`, `list`, `update` (BR-12 + re-validate SL/TP), `close` (BR-10, set editable_until), `soft_delete` (BR-29). Private validators: `_validate_sl_tp`, `_validate_exit_consistency`, `_validate_editable` |
| `app/modules/trades/schemas.py` | Create | `TradeCreate`, `TradeUpdate`, `TradeClose`, `TradeResponse` (all `from_attributes=True`), `TradeFilters(PaginationParams)` |
| `app/modules/trades/router.py` | Create | 6 endpoints via `Depends(get_trade_service)` provider: POST `/api/trades` (201), GET `/api/trades` (paginated), GET `/api/trades/{id}`, PATCH `/api/trades/{id}`, DELETE `/api/trades/{id}` (204), POST `/api/trades/{id}/close` |
| `tests/modules/trades/__init__.py` | Create | Package init |
| `tests/modules/trades/test_repository.py` | Create | 12 tests: CRUD, each filter, pagination, soft-delete, nonexistent get |
| `tests/modules/trades/test_service.py` | Create | 14 tests: BR-07 (4), BR-08 (2), BR-09 (2), BR-10 (3), BR-12 (2), BR-29 (1) |
| `tests/modules/trades/test_endpoints.py` | Create | 12 tests: create open/closed, invalid SL, missing required, list paginated, filter by status, get by ID, get 404, patch valid, patch past editable (409), delete (204), close |

### Dependencies
- Task 1: Foundation

### Business Rules
- **BR-07**: SL correct side (long: SL < entry; short: SL > entry) — enforced on create and update
- **BR-08**: TP correct side (long: TP > entry; short: TP < entry) — enforced on create and update
- **BR-09**: SL and TP on opposite sides of entry — enforced on create and update
- **BR-10**: exit_price and exit_datetime both NULL or both set; closed requires both — enforced on create and close
- **BR-12**: 30-day soft-lock (editable_until in future) — enforced on update
- **BR-29**: DELETE sets `is_active=False`, does NOT change `status`

### Acceptance Criteria
- [ ] POST `/api/trades` with valid open trade returns 201 + `TradeResponse` with `status="open"`, no exit fields
- [ ] POST `/api/trades` with valid closed trade returns 201 + exit fields present + `editable_until` set to 30 days from entry
- [ ] POST `/api/trades` with SL on wrong side (long SL > entry) returns 422 with `business_rule_violation`
- [ ] POST `/api/trades` with SL/TP on same side returns 422
- [ ] POST `/api/trades` with `status="closed"` but missing exit_price returns 422
- [ ] PATCH `/api/trades/{id}` within editable window succeeds; past it returns 409
- [ ] DELETE `/api/trades/{id}` returns 204 and sets `is_active=False`, `status` unchanged
- [ ] POST `/api/trades/{id}/close` sets `status="closed"` and `editable_until`; rejecting already-closed returns 422
- [ ] Router auto-discovered by `discover_modules()`

### Required Tests
| File | Tests | Coverage |
|------|-------|----------|
| `tests/modules/trades/test_repository.py` | 12 | CRUD, all filter params, pagination, soft-delete, nonexistent |
| `tests/modules/trades/test_service.py` | 14 | BR-07 long valid/invalid (2), BR-07 short valid/invalid (2), BR-08 valid/invalid (2), BR-09 opposite/same (2), BR-10 closed/open/missing (3), BR-12 future/past (2), BR-29 (1) |
| `tests/modules/trades/test_endpoints.py` | 12 | 201 create open/closed, 422 invalid SL/missing/exit, 200 list paginated/filtered/get-by-id, 404, 200 patch/past-409, 204 delete, 200 close |

### Line Estimate
~500 lines (highest in the stack — see Review Workload Forecast note above). If over 400-line budget, consider `size:exception` for this PR, or split service tests into a follow-up PR within the trades concern.

---

## Task 4: Accounts

### Files
| File | Action | Description |
|------|--------|-------------|
| `app/modules/accounts/__init__.py` | Create | Package init |
| `app/modules/accounts/repository.py` | Create | `AccountRepository` with `get_by_name()`, filtered `list()` (status, search, is_active, pagination) |
| `app/modules/accounts/service.py` | Create | `AccountService` with `create` (name unique check), `get`, `list`, `update` (name uniqueness if changed), `soft_delete` |
| `app/modules/accounts/schemas.py` | Create | `AccountCreate`, `AccountUpdate`, `AccountResponse` (`from_attributes=True`), `AccountFilters(PaginationParams)` |
| `app/modules/accounts/router.py` | Create | 5 endpoints via `Depends(get_account_service)` provider: POST `/api/accounts` (201), GET `/api/accounts`, GET `/api/accounts/{id}`, PATCH `/api/accounts/{id}`, DELETE `/api/accounts/{id}` (204) |
| `tests/modules/accounts/__init__.py` | Create | Package init |
| `tests/modules/accounts/test_repository.py` | Create | 8 tests: add/get, nonexistent get, update, delete soft, duplicate name raises IntegrityError, status filter, search filter, pagination |
| `tests/modules/accounts/test_service.py` | Create | 6 tests: create success, duplicate name → ConflictError, get nonexistent → NotFoundError, update name, update duplicate name → ConflictError, soft_delete |
| `tests/modules/accounts/test_endpoints.py` | Create | 6 tests: POST 201, duplicate name 409, GET list paginated, GET by ID, PATCH, DELETE 204 |

### Dependencies
- Task 1: Foundation

### Business Rules
- **BR-26**: Account name DB UNIQUE — enforced at service level via `get_by_name()` check before create/update

### Acceptance Criteria
- [ ] POST `/api/accounts` with valid data returns 201 + `AccountResponse`
- [ ] POST `/api/accounts` with duplicate name returns 409 with conflict detail
- [ ] GET `/api/accounts` returns paginated `AccountResponse` list; `?status=inactive` filters correctly
- [ ] GET `/api/accounts/{id}` returns 200 for existing, 404 for missing
- [ ] PATCH `/api/accounts/{id}` updates fields; changing to existing name returns 409
- [ ] DELETE `/api/accounts/{id}` returns 204 with `is_active=False`
- [ ] Router auto-discovered by `discover_modules()`

### Required Tests
| File | Tests | Coverage |
|------|-------|----------|
| `tests/modules/accounts/test_repository.py` | 8 | CRUD, name uniqueness, status/search filters, pagination |
| `tests/modules/accounts/test_service.py` | 6 | Create, duplicate → 409, nonexistent → 404, update, duplicate-update → 409, soft-delete |
| `tests/modules/accounts/test_endpoints.py` | 6 | POST 201, POST dup 409, GET list, GET by ID, PATCH, DELETE 204 |

### Line Estimate
~375 lines

---

## Task 5: Assets

### Files
| File | Action | Description |
|------|--------|-------------|
| `app/modules/assets/__init__.py` | Create | Package init |
| `app/modules/assets/repository.py` | Create | `AssetRepository` with `get_by_symbol_market()`, filtered `list()` (symbol, market_id, search, is_active, pagination) |
| `app/modules/assets/service.py` | Create | `AssetService` with `create` (validate market exists, symbol+market unique), `get`, `list`, `update` (re-validate uniqueness if symbol/market_id changed, validate market if market_id changed), `soft_delete` |
| `app/modules/assets/schemas.py` | Create | `AssetCreate`, `AssetUpdate`, `AssetResponse` (`from_attributes=True`), `AssetFilters(PaginationParams)` |
| `app/modules/assets/router.py` | Create | 5 endpoints via `Depends(get_asset_service)` provider: POST `/api/assets` (201), GET `/api/assets`, GET `/api/assets/{id}`, PATCH `/api/assets/{id}`, DELETE `/api/assets/{id}` (204) |
| `tests/modules/assets/__init__.py` | Create | Package init |
| `tests/modules/assets/test_repository.py` | Create | 8 tests: add/get, nonexistent, duplicate symbol+market, update, soft-delete, symbol filter, market_id filter, (symbol + market_id) filter |
| `tests/modules/assets/test_service.py` | Create | 6 tests: create success, duplicate symbol+market → ConflictError, missing market_id → BusinessRuleError, get → NotFoundError, update with new market_id that doesn't exist → BusinessRuleError, soft_delete |
| `tests/modules/assets/test_endpoints.py` | Create | 6 tests: POST 201, duplicate 409, missing market 422, GET list with symbol filter, GET by ID, DELETE 204 |

### Dependencies
- Task 1: Foundation

### Business Rules
- **BR-16**: (symbol, market_id) DB UNIQUE — enforced at service level via `get_by_symbol_market()` check before create/update

### Acceptance Criteria
- [ ] POST `/api/assets` with valid data returns 201 + `AssetResponse`
- [ ] POST `/api/assets` with duplicate (symbol + market_id) returns 409
- [ ] POST `/api/assets` with non-existent market_id returns 422
- [ ] GET `/api/assets` returns paginated assets; `?symbol=X&market_id=Y` filters correctly
- [ ] GET `/api/assets/{id}` returns 200 for existing, 404 for missing
- [ ] PATCH `/api/assets/{id}` updates fields; changing symbol to existing combo returns 409
- [ ] DELETE `/api/assets/{id}` returns 204 with `is_active=False`
- [ ] Router auto-discovered by `discover_modules()`

### Required Tests
| File | Tests | Coverage |
|------|-------|----------|
| `tests/modules/assets/test_repository.py` | 8 | CRUD, uniqueness, symbol/market_id/search filters |
| `tests/modules/assets/test_service.py` | 6 | Create, dup → 409, missing market → 422, nonexistent → 404, update with bad market, soft-delete |
| `tests/modules/assets/test_endpoints.py` | 6 | POST 201, POST dup 409, POST bad market 422, GET with filter, GET by ID, DELETE 204 |

### Line Estimate
~390 lines

---

## Task 6: Integration

### Files
| File | Action | Description |
|------|--------|-------------|
| `tests/modules/__init__.py` | Create | Package init for tests/modules/ |
| `tests/test_app_integration.py` | Create | End-to-end smoke test: create app, verify ALL 22+ endpoints registered (no 405/404 stubs), verify OpenAPI spec renders, verify error handler format across all error types |

### Dependencies
- Task 1: Foundation
- Task 2: Catalogs
- Task 3: Trades
- Task 4: Accounts
- Task 5: Assets

### Business Rules
- NFR-01 (API-first — OpenAPI docs)
- NFR-04 (Standardized errors)
- NFR-05 (Pagination)
- NFR-10 (One UoW per request)

### Acceptance Criteria
- [ ] `create_app()` returns fully configured FastAPI app with all 4 module routers registered
- [ ] GET `/api/trades`, `/api/accounts`, `/api/assets`, `/api/markets` all return valid responses (not 404/405)
- [ ] OpenAPI schema (`GET /openapi.json`) includes all endpoint paths and Pydantic schemas
- [ ] Error handler formats: 404 returns `{"detail": "..."}`, 422 returns Pydantic-style array for business rule violations
- [ ] All 86 tests pass with `pytest tests/ -x --tb=short` (no test failures, no import errors)

### Required Tests
| File | Tests | Coverage |
|------|-------|----------|
| `tests/test_app_integration.py` | 4 | App creation + all endpoint registration (1), OpenAPI schema completeness (1), error handler format 404 (1), error handler format 422 (1) |
| All module tests | 86 | Full regression (implicit) |

### Line Estimate
~100 lines

---

## Dependency Graph

```
Foundation (no deps)
  ├── Catalogs (deps: Foundation)
  ├── Trades (deps: Foundation)
  ├── Accounts (deps: Foundation)
  ├── Assets (deps: Foundation)
  └── Integration (deps: all above)
```

Foundation must be PR #1. Catalogs, Trades, Accounts, and Assets are independent of each other (any order after Foundation). Integration is last — it verifies the fully wired application.

## Implementation Notes

1. **Module router auto-discovery**: Existing `discover_modules()` in `app/modules/__init__.py` automatically finds any `router.py` in subdirectories of `app/modules/`. No manual routing registration needed in `app/main.py`.

2. **UoW late imports**: `UnitOfWork` repo properties use lazy imports (`from app.modules.trades.repository import TradeRepository` inside the property getter) to avoid import errors before modules exist. This is intentional — the imports happen at first access, not at class load time.

3. **`get_db()` in dependencies.py**: Uses the existing `async_session_factory` from `app.database` (not `app.db.database`). No file moves required.

4. **`tests/conftest.py` is created in Foundation** because all module tests depend on its async fixtures (in-memory engine, test client, UoW). This enables each module PR to run its tests independently.

5. **Service providers in `app/db/dependencies.py` with late imports**: Foundation creates provider functions (`get_trade_service`, `get_account_service`, `get_asset_service`, `get_broker_service`) that use `from app.modules.{module}.service import {Service}` inside the function body. This is safe because the import only runs when the function is called (at request time), by which point all module packages exist. Using `Depends(provider)` in routers enables `app.dependency_overrides[get_trade_service]` in tests.

6. **Trades PR size risk**: ~500 lines is above the 400-line budget. Options: (a) accept `size:exception` to keep the module intact per the "one module = one task" rule, or (b) split into two stacked PRs: Trades-core (repo + service + schemas + router + repo/service tests) and Trades-endpoints (endpoint tests + integration). The user's "one module per task" constraint favors option (a).
