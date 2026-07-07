# Application Layer Specification

> **Change**: `tip-application-layer` — adds repository, unit-of-work, service, DTO, and endpoint layers on top of the existing domain model. No DB schema changes. No new columns, tables, or constraints.

---

## 1. Functional Requirements

### 1.1 Trade CRUD (`trade-crud`)

The system MUST expose full CRUD + close + soft-delete for the `Trade` entity via REST endpoints. All writes enforce service-layer BRs.

| Ref | Endpoint | Method | Purpose | BRs |
|-----|----------|--------|---------|-----|
| TRD-01 | `/api/trades` | POST | Create trade (open or closed) | BR-07, BR-08, BR-09, BR-10, BR-04/03/02 (DB) |
| TRD-02 | `/api/trades` | GET | List trades with filters + pagination | — |
| TRD-03 | `/api/trades/{id}` | GET | Get single trade by ID | — |
| TRD-04 | `/api/trades/{id}` | PATCH | Update trade within editable_until | BR-12, BR-07, BR-08, BR-09 |
| TRD-05 | `/api/trades/{id}` | DELETE | Soft-delete (`is_active=False`, status unchanged) | BR-29 |
| TRD-06 | `/api/trades/{id}/close` | POST | Close trade (set exit_price + exit_datetime) | BR-10 |

**Business rules enforced:**

- **BR-07** (SL correct side): For long direction, `stop_loss < entry_price`. For short direction, `stop_loss > entry_price`. If `stop_loss` is NULL, skip. Enforced on Create and Update.
- **BR-08** (TP correct side): For long direction, `take_profit > entry_price`. For short direction, `take_profit < entry_price`. If `take_profit` is NULL, skip. Enforced on Create and Update.
- **BR-09** (SL/TP opposite): If both SL and TP are provided, they MUST be on opposite sides of entry. The market between SL and entry is "stop territory" — TP MUST NOT be on the same side as SL. Enforced on Create and Update.
- **BR-10** (Exit consistency): `exit_price` and `exit_datetime` MUST both be set or both be NULL. When creating with `status='closed'`, both are REQUIRED. When `status='open'`, both MUST be NULL. Enforced on Create and Close.
- **BR-12** (30-day soft-lock): On Update, check `editable_until` is either NULL (never locked) or in the future (still editable). If `editable_until` is in the past, reject with 409 Conflict.
- **BR-29** (Soft-delete only): DELETE sets `is_active=False`. Does NOT change `status` (remains 'open' or 'closed'). `status='archived'` requires a future domain model SDD.

**Filters** (`GET /api/trades`):

| Parameter | Type | Behavior |
|-----------|------|----------|
| `status` | str | `open` or `closed` |
| `direction` | str | `long` or `short` |
| `account_id` | int | Exact match |
| `asset_id` | int | Exact match |
| `date_from` | str (ISO 8601) | `entry_datetime >= date_from` |
| `date_to` | str (ISO 8601) | `entry_datetime <= date_to` |
| `search` | str | LIKE match on `notes_override` |
| `is_active` | bool | Default `true`. Set `false` to include soft-deleted |

**Error conditions:**

| Condition | Status | Detail |
|-----------|--------|--------|
| Trade not found | 404 | `"Trade with id {id} not found"` |
| Past editable_until | 409 | `"Trade with id {id} is past its editable window (editable_until: {editable_until})"` |
| SL/TP validation failure | 422 | Pydantic-style validation error |
| Exit consistency violation | 422 | Pydantic-style validation error |

---

### 1.2 Account CRUD (`account-crud`)

The system MUST expose full CRUD for Account with status toggle.

| Ref | Endpoint | Method | Purpose | BRs |
|-----|----------|--------|---------|-----|
| ACC-01 | `/api/accounts` | POST | Create account | BR-26 (DB UNIQUE) |
| ACC-02 | `/api/accounts` | GET | List accounts with filters | — |
| ACC-03 | `/api/accounts/{id}` | GET | Get single account | — |
| ACC-04 | `/api/accounts/{id}` | PATCH | Update name or status | BR-27 (DB CHECK) |
| ACC-05 | `/api/accounts/{id}` | DELETE | Soft-delete (`is_active=False`) | — |

**Filters** (`GET /api/accounts`):

| Parameter | Type | Behavior |
|-----------|------|----------|
| `status` | str | `active` or `inactive` |
| `search` | str | LIKE match on `name` |
| `is_active` | bool | Default `true` |

**Error conditions:**

| Condition | Status | Detail |
|-----------|--------|--------|
| Account not found | 404 | `"Account with id {id} not found"` |
| Duplicate name | 409 | `"Account with name '{name}' already exists"` |

---

### 1.3 Asset CRUD (`asset-crud`)

The system MUST expose full CRUD for Asset with market filtering.

| Ref | Endpoint | Method | Purpose | BRs |
|-----|----------|--------|---------|-----|
| AST-01 | `/api/assets` | POST | Create asset | BR-16 (DB UNIQUE) |
| AST-02 | `/api/assets` | GET | List assets with filters | — |
| AST-03 | `/api/assets/{id}` | GET | Get single asset | — |
| AST-04 | `/api/assets/{id}` | PATCH | Update symbol, name, market_id | BR-16 |
| AST-05 | `/api/assets/{id}` | DELETE | Soft-delete (`is_active=False`) | — |

**Filters** (`GET /api/assets`):

| Parameter | Type | Behavior |
|-----------|------|----------|
| `symbol` | str | Exact match |
| `market_id` | int | Exact match |
| `search` | str | LIKE match on `name` |
| `is_active` | bool | Default `true` |

**Error conditions:**

| Condition | Status | Detail |
|-----------|--------|--------|
| Asset not found | 404 | `"Asset with id {id} not found"` |
| Duplicate symbol+market | 409 | `"Asset with symbol '{symbol}' and market_id {market_id} already exists"` |
| Market not found | 422 | `"Market with id {market_id} does not exist"` |

---

### 1.4 Catalog Read (`catalog-read`)

The system MUST expose read-only GET endpoints for seeded and user-defined catalog entities.

| Ref | Endpoint | Method | Purpose | Access |
|-----|----------|--------|---------|--------|
| CAT-01 | `/api/markets` | GET | List all markets | Seeded catalog |
| CAT-02 | `/api/market-sessions` | GET | List all market sessions | Seeded catalog |
| CAT-03 | `/api/timeframes` | GET | List all timeframes | Seeded catalog |
| CAT-04 | `/api/brokers` | GET | List all brokers | User-defined |
| CAT-05 | `/api/brokers/{id}` | GET | Get broker by ID | User-defined |

**Business rules:**

- **BR-17** (Broker name SHOULD be unique): On Broker create (not in MVP as standalone endpoint, but enforced if creation is supported via seed/admin), the service SHOULD warn/validate name uniqueness at the service level. No DB UNIQUE constraint.

**Error conditions:**

| Condition | Status | Detail |
|-----------|--------|--------|
| Broker not found | 404 | `"Broker with id {id} not found"` |

---

## 2. Non-Functional Requirements

| ID | Requirement | Specification |
|----|-------------|---------------|
| NFR-01 | **API-first** | All endpoints MUST be documented via OpenAPI 3.1 (auto-generated by FastAPI). Every request and response body MUST have a Pydantic schema. |
| NFR-02 | **Async throughout** | All repositories, services, and endpoint handlers MUST be async (`async def`). SQLAlchemy `AsyncSession` MUST be used for all DB access. |
| NFR-03 | **Isolated test DB** | Integration tests MUST use a separate SQLite database file or in-memory database. Tests MUST NOT write to the development database. |
| NFR-04 | **Standardized errors** | All error responses MUST follow the format in §5. Validation errors use FastAPI/Pydantic default 422 format. Custom 404/409 use the simple `{"detail": "message"}` format. |
| NFR-05 | **Pagination** | All list endpoints MUST return paginated responses following §6 format. Default `page=1, page_size=20`. Maximum `page_size=100`. |
| NFR-06 | **No DB schema changes** | This phase MUST NOT alter any table, constraint, index, or column. Soft-delete uses existing `is_active` column only. |
| NFR-07 | **DTO separation** | Every entity with write operations MUST have distinct Create, Update, and Response schemas. No single "model" DTO. |
| NFR-08 | **Zero business logic in repositories** | Repositories MUST contain only data access code. No domain logic. |
| NFR-09 | **Single authoritative service layer** | All business rule enforcement MUST live in service methods. Endpoints MUST call services, not enforce rules themselves. |
| NFR-10 | **One UoW per request** | Each HTTP request MUST create exactly one `UnitOfWork` instance. Commit/rollback boundary is the request lifecycle. |

---

## 3. DTO Specifications

### 3.1 Trade DTOs

**TradeCreate** (`POST /api/trades`):

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `account_id` | int | YES | — | Must reference existing Account |
| `asset_id` | int | YES | — | Must reference existing Asset |
| `direction` | str | YES | — | `'long'` or `'short'` |
| `status` | str | YES | — | `'open'` or `'closed'` |
| `entry_price` | float | YES | — | Must be > 0 |
| `quantity` | float | YES | — | Must be > 0 |
| `entry_datetime` | str (ISO 8601) | YES | — | — |
| `exit_price` | float? | conditional | — | Required if `status='closed'`; forbidden if `status='open'` |
| `exit_datetime` | str (ISO 8601)? | conditional | — | Required if `status='closed'`; forbidden if `status='open'` |
| `stop_loss` | float? | NO | null | BR-07, BR-09 enforced |
| `take_profit` | float? | NO | null | BR-08, BR-09 enforced |
| `position_size` | float? | NO | null | Must be >= 0 if provided |
| `commission` | float | NO | 0.0 | Must be >= 0 |
| `swap_fees` | float | NO | 0.0 | Must be >= 0 |
| `risk_amount` | float? | NO | null | — |
| `broker_id` | int? | NO | null | Must reference existing Broker |
| `market_session_id` | int? | NO | null | Must reference existing MarketSession |
| `timeframe_id` | int? | NO | null | Must reference existing Timeframe |
| `notes_override` | str? | NO | null | — |

**TradeUpdate** (`PATCH /api/trades/{id}`):

All fields optional. Only provided fields are updated. Validates BR-07, BR-08, BR-09, BR-12.

| Field | Type | Notes |
|-------|------|-------|
| `entry_price` | float? | Must be > 0 |
| `quantity` | float? | Must be > 0 |
| `entry_datetime` | str (ISO 8601)? | — |
| `stop_loss` | float? | null = clear |
| `take_profit` | float? | null = clear |
| `position_size` | float? | null = clear, must be >= 0 if provided |
| `commission` | float? | Must be >= 0 |
| `swap_fees` | float? | Must be >= 0 |
| `risk_amount` | float? | null = clear |
| `direction` | str? | `'long'` or `'short'` — changing direction re-validates SL/TP |
| `notes_override` | str? | null = clear |
| `broker_id` | int? | null = clear |
| `market_session_id` | int? | null = clear |
| `timeframe_id` | int? | null = clear |

**TradeClose** (`POST /api/trades/{id}/close`):

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `exit_price` | float | YES | Must be > 0 |
| `exit_datetime` | str (ISO 8601) | YES | — |

**TradeResponse**:

Returns all Trade fields (computed metrics excluded — PnL, PnL points, R multiple are computed on-the-fly on the client side).

| Field | Type | Notes |
|-------|------|-------|
| `id` | int | — |
| `account_id` | int | — |
| `asset_id` | int | — |
| `direction` | str | — |
| `status` | str | `'open'` or `'closed'` |
| `entry_price` | float | — |
| `exit_price` | float? | — |
| `quantity` | float | — |
| `stop_loss` | float? | — |
| `take_profit` | float? | — |
| `position_size` | float? | — |
| `commission` | float | — |
| `swap_fees` | float | — |
| `risk_amount` | float? | — |
| `entry_datetime` | str | — |
| `exit_datetime` | str? | — |
| `editable_until` | str? | — |
| `notes_override` | str? | — |
| `broker_id` | int? | — |
| `market_session_id` | int? | — |
| `timeframe_id` | int? | — |
| `is_active` | bool | — |
| `created_at` | str | — |
| `updated_at` | str? | — |

### 3.2 Account DTOs

**AccountCreate**:

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `name` | str | YES | — | Must be unique |
| `broker` | str? | NO | null | — |
| `account_type` | str? | NO | null | — |
| `base_currency` | str | NO | `'USD'` | — |
| `status` | str | NO | `'active'` | Must be `'active'` or `'inactive'` |

**AccountUpdate**:

| Field | Type | Notes |
|-------|------|-------|
| `name` | str? | Must be unique if changed |
| `broker` | str? | null = clear |
| `account_type` | str? | null = clear |
| `base_currency` | str? | — |
| `status` | str? | `'active'` or `'inactive'` |

**AccountResponse**:

| Field | Type |
|-------|------|
| `id` | int |
| `name` | str |
| `broker` | str? |
| `account_type` | str? |
| `base_currency` | str |
| `status` | str |
| `is_active` | bool |
| `created_at` | str |
| `updated_at` | str? |

### 3.3 Asset DTOs

**AssetCreate**:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `symbol` | str | YES | Combined with market_id must be unique |
| `name` | str? | NO | — |
| `market_id` | int | YES | Must reference existing Market |

**AssetUpdate**:

| Field | Type | Notes |
|-------|------|-------|
| `symbol` | str? | Combined with market_id must be unique |
| `name` | str? | null = clear |
| `market_id` | int? | Must reference existing Market |

**AssetResponse**:

| Field | Type |
|-------|------|
| `id` | int |
| `symbol` | str |
| `name` | str? |
| `market_id` | int |
| `is_active` | bool |
| `created_at` | str |
| `updated_at` | str? |

### 3.4 Catalog DTOs

**MarketResponse**: `{ id: int, name: str, created_at: str }`
**MarketSessionResponse**: `{ id: int, name: str, created_at: str }`
**TimeframeResponse**: `{ id: int, name: str, created_at: str }`
**BrokerCreate**: `{ name: str }`
**BrokerUpdate**: `{ name: str? }`
**BrokerResponse**: `{ id: int, name: str, is_active: bool, created_at: str, updated_at: str? }`

---

## 4. Error Response Format

### 4.1 Validation Error (422)

Uses FastAPI/Pydantic default format:

```json
{
  "detail": [
    {
      "type": "greater_than",
      "loc": ["body", "entry_price"],
      "msg": "Input should be greater than 0",
      "input": 0
    }
  ]
}
```

### 4.2 Not Found (404)

```json
{
  "detail": "Trade with id 42 not found"
}
```

### 4.3 Conflict (409)

```json
{
  "detail": "Trade with id 42 is past its editable window (editable_until: 2026-06-06T15:00:00.000Z)"
}
```

### 4.4 Domain Error (422)

Business rule violations that aren't caught by Pydantic validation use 422 with a descriptive message:

```json
{
  "detail": [
    {
      "type": "business_rule_violation",
      "loc": ["body", "stop_loss"],
      "msg": "Stop loss must be below entry price for long trades (entry: 1.1000, sl: 1.1500)",
      "input": 1.15
    }
  ]
}
```

---

## 5. Pagination Format

All list endpoints MUST return:

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

| Field | Type | Description |
|-------|------|-------------|
| `items` | list[ResponseDTO] | The page of results |
| `total` | int | Total number of matching records |
| `page` | int | Current page number (1-indexed) |
| `page_size` | int | Number of items per page |
| `pages` | int | Total number of pages (`ceil(total / page_size)`) |

Query parameters: `?page=1&page_size=20`. Default: `page=1`, `page_size=20`. Max `page_size=100`.

---

## 6. Repository Contracts

All repositories inherit from a generic `AbstractRepository[T]` base and implement `SqlAlchemyRepository[T]` with standard CRUD.

### 6.1 AbstractRepository (Protocol)

```python
class AbstractRepository[T]:
    async def add(self, entity: T) -> T: ...
    async def get(self, id: int) -> T | None: ...
    async def list(self, **filters) -> tuple[list[T], int]: ...
    async def update(self, entity: T) -> T: ...
    async def delete(self, entity: T) -> None: ...
```

### 6.2 TradeRepository

```python
class TradeRepository(SqlAlchemyRepository[Trade]):
    async def add(self, trade: Trade) -> Trade
    async def get(self, id: int) -> Trade | None
    async def list(
        self, *,
        status: str | None = None,
        direction: str | None = None,
        account_id: int | None = None,
        asset_id: int | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        search: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Trade], int]: ...
    async def update(self, trade: Trade) -> Trade
    async def delete(self, trade: Trade) -> None
    async def count_by_account(self, account_id: int) -> int  # for cascade checks
```

### 6.3 AccountRepository

```python
class AccountRepository(SqlAlchemyRepository[Account]):
    async def add(self, account: Account) -> Account
    async def get(self, id: int) -> Account | None
    async def get_by_name(self, name: str) -> Account | None
    async def list(
        self, *,
        status: str | None = None,
        search: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Account], int]: ...
    async def update(self, account: Account) -> Account
    async def delete(self, account: Account) -> None
```

### 6.4 AssetRepository

```python
class AssetRepository(SqlAlchemyRepository[Asset]):
    async def add(self, asset: Asset) -> Asset
    async def get(self, id: int) -> Asset | None
    async def get_by_symbol_market(self, symbol: str, market_id: int) -> Asset | None
    async def list(
        self, *,
        symbol: str | None = None,
        market_id: int | None = None,
        search: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Asset], int]: ...
    async def update(self, asset: Asset) -> Asset
    async def delete(self, asset: Asset) -> None
```

### 6.5 Catalog Repositories

```python
class MarketRepository(SqlAlchemyRepository[Market]):
    async def list_all(self) -> list[Market]
    async def get(self, id: int) -> Market | None

class MarketSessionRepository(SqlAlchemyRepository[MarketSession]):
    async def list_all(self) -> list[MarketSession]
    async def get(self, id: int) -> MarketSession | None

class TimeframeRepository(SqlAlchemyRepository[Timeframe]):
    async def list_all(self) -> list[Timeframe]
    async def get(self, id: int) -> Timeframe | None

class BrokerRepository(SqlAlchemyRepository[Broker]):
    async def add(self, broker: Broker) -> Broker  # BR-17
    async def get(self, id: int) -> Broker | None
    async def list_all(self) -> list[Broker]
    async def get_by_name(self, name: str) -> Broker | None  # BR-17 uniqueness check
```

---

## 7. Service Contracts

### 7.1 TradeService

```python
class TradeService:
    async def create(self, dto: TradeCreate, uow: UnitOfWork) -> Trade
        # BR-07: validates SL side
        # BR-08: validates TP side
        # BR-09: validates SL/TP opposite
        # BR-10: validates exit pair consistency
        # Sets editable_until = entry_datetime + 30 days (only if status='closed')

    async def get(self, id: int, uow: UnitOfWork) -> Trade
        # Returns None → endpoint raises 404

    async def list(
        self, filters: TradeFilters, uow: UnitOfWork
    ) -> tuple[list[Trade], int]:
        # Delegates to repository with validated filters

    async def update(self, id: int, dto: TradeUpdate, uow: UnitOfWork) -> Trade
        # BR-12: checks editable_until before update
        # BR-07, BR-08, BR-09: re-validates if SL/TP/direction changed

    async def close(self, id: int, dto: TradeClose, uow: UnitOfWork) -> Trade
        # BR-10: validates exit_price and exit_datetime both set
        # Sets status='closed', sets editable_until = now + 30 days
        # Rejects if already closed

    async def soft_delete(self, id: int, uow: UnitOfWork) -> None
        # BR-29: sets is_active=False, does NOT change status
```

**Domain rules enforced at service level:**

```python
def _validate_sl_tp(self, direction: str, entry_price: float,
                    stop_loss: float | None, take_profit: float | None) -> None:
    """Enforce BR-07, BR-08, BR-09."""
    if stop_loss is not None:
        if direction == 'long' and stop_loss >= entry_price:
            raise DomainError("SL must be below entry for long trades")
        if direction == 'short' and stop_loss <= entry_price:
            raise DomainError("SL must be above entry for short trades")
    if take_profit is not None:
        if direction == 'long' and take_profit <= entry_price:
            raise DomainError("TP must be above entry for long trades")
        if direction == 'short' and take_profit >= entry_price:
            raise DomainError("TP must be below entry for short trades")
    if stop_loss is not None and take_profit is not None:
        # BR-09: SL and TP on opposite sides of entry
        sl_side = stop_loss < entry_price  # True = below entry
        tp_side = take_profit < entry_price  # True = below entry
        if sl_side == tp_side:
            raise DomainError("SL and TP must be on opposite sides of entry price")


def _validate_editable(self, trade: Trade) -> None:
    """Enforce BR-12: 30-day soft-lock."""
    if trade.editable_until is not None:
        if datetime.now(UTC).isoformat() > trade.editable_until:
            raise DomainError(
                f"Trade is past its editable window (editable_until: {trade.editable_until})"
            )
```

### 7.2 AccountService

```python
class AccountService:
    async def create(self, dto: AccountCreate, uow: UnitOfWork) -> Account
        # Checks name uniqueness via repository query (DB UNIQUE handles race)
        # Returns 409 if duplicate

    async def get(self, id: int, uow: UnitOfWork) -> Account
    async def list(self, filters: AccountFilters, uow: UnitOfWork) -> tuple[list[Account], int]
    async def update(self, id: int, dto: AccountUpdate, uow: UnitOfWork) -> Account
        # Checks name uniqueness if name changed
    async def soft_delete(self, id: int, uow: UnitOfWork) -> None
        # Sets is_active=False
```

### 7.3 AssetService

```python
class AssetService:
    async def create(self, dto: AssetCreate, uow: UnitOfWork) -> Asset
        # Validates market_id exists
        # Checks symbol+market uniqueness

    async def get(self, id: int, uow: UnitOfWork) -> Asset
    async def list(self, filters: AssetFilters, uow: UnitOfWork) -> tuple[list[Asset], int]
    async def update(self, id: int, dto: AssetUpdate, uow: UnitOfWork) -> Asset
        # Re-validates symbol+market uniqueness if changed
    async def soft_delete(self, id: int, uow: UnitOfWork) -> None
        # Sets is_active=False
```

### 7.4 CatalogServices

```python
class BrokerService:
    async def create(self, dto: BrokerCreate, uow: UnitOfWork) -> Broker
        # BR-17: warns/suggests uniqueness (service-level, not enforced)

    async def get(self, id: int, uow: UnitOfWork) -> Broker
    async def list_all(self, uow: UnitOfWork) -> list[Broker]
```

---

## 8. Unit of Work Contract

```python
class UnitOfWork:
    """Single transaction boundary per request."""

    def __init__(self, session: AsyncSession): ...

    # Repository accessors (properties, lazy-init)
    trades: TradeRepository
    accounts: AccountRepository
    assets: AssetRepository
    markets: MarketRepository
    market_sessions: MarketSessionRepository
    timeframes: TimeframeRepository
    brokers: BrokerRepository

    async def commit(self) -> None:
        """Commit the current transaction. Raises on conflict."""

    async def rollback(self) -> None:
        """Rollback the current transaction."""

    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(self, *args) -> None:
        """Rollback on exception, no-op on success (caller commits explicitly)."""
```

The UoW SHALL be used via FastAPI dependency:

```python
async def get_uow(db: AsyncSession = Depends(get_db)) -> AsyncGenerator[UnitOfWork, None]:
    uow = UnitOfWork(db)
    async with uow:
        yield uow
        await uow.commit()
```

---

## 9. Test Specifications

### 9.1 Repository Tests

| Test | Layer | What it verifies |
|------|-------|-----------------|
| `test_add_and_get_trade` | Repository | Add trade, get by ID returns correct object |
| `test_get_nonexistent_trade` | Repository | Get non-existent ID returns None |
| `test_list_trades_with_filters` | Repository | Each filter parameter narrows results correctly |
| `test_list_trades_pagination` | Repository | Page/page_size returns correct slice and total |
| `test_update_trade` | Repository | Update field persists correctly |
| `test_delete_trade` | Repository | Soft-delete sets is_active=False |
| `test_add_duplicate_account_name` | Repository | Duplicate name raises IntegrityError |
| `test_add_duplicate_asset_symbol_market` | Repository | Duplicate symbol+market raises IntegrityError |
| `test_list_accounts_with_status_filter` | Repository | Status filter works |
| `test_list_assets_with_market_filter` | Repository | Market_id filter works |

### 9.2 Service Tests

| Test | BR | What it verifies |
|------|----|-----------------|
| `test_create_long_trade_valid_sl` | BR-07 | SL=0.9, entry=1.0, direction=long → succeeds |
| `test_create_long_trade_invalid_sl` | BR-07 | SL=1.1, entry=1.0, direction=long → DomainError |
| `test_create_short_trade_valid_sl` | BR-07 | SL=1.1, entry=1.0, direction=short → succeeds |
| `test_create_short_trade_invalid_sl` | BR-07 | SL=0.9, entry=1.0, direction=short → DomainError |
| `test_create_long_trade_valid_tp` | BR-08 | TP=1.1, entry=1.0, direction=long → succeeds |
| `test_create_long_trade_invalid_tp` | BR-08 | TP=0.9, entry=1.0, direction=long → DomainError |
| `test_create_trade_sl_tp_opposite` | BR-09 | SL=0.9, TP=1.1, entry=1.0, long → succeeds |
| `test_create_trade_sl_tp_same_side` | BR-09 | SL=0.9, TP=0.95, entry=1.0, long → DomainError |
| `test_create_closed_trade_with_exit` | BR-10 | status=closed, exit_price=1.1, exit_datetime=now → succeeds |
| `test_create_closed_trade_missing_exit_price` | BR-10 | status=closed, exit_price=null → DomainError |
| `test_create_open_trade_with_exit` | BR-10 | status=open, exit_price=1.1 → DomainError |
| `test_update_within_editable_window` | BR-12 | editable_until=+1d → update succeeds |
| `test_update_past_editable_window` | BR-12 | editable_until=-1d → DomainError |
| `test_soft_delete_trade` | BR-29 | soft_delete sets is_active=False, status unchanged |
| `test_close_trade` | BR-10 | Close with valid exit updates status and sets editable_until |
| `test_close_already_closed_trade` | — | Close already-closed trade → DomainError |
| `test_create_account_duplicate_name` | BR-26 | Same name → 409/DomainError |
| `test_create_asset_duplicate_symbol_market` | BR-16 | Same symbol+market → DomainError |

### 9.3 Endpoint Integration Tests

| Test | What it verifies |
|------|-----------------|
| `POST /api/trades — valid open trade` | 201 + response matches TradeResponse schema |
| `POST /api/trades — valid closed trade` | 201 + exit fields present |
| `POST /api/trades — invalid SL` | 422 with validation error detail |
| `POST /api/trades — missing required field` | 422 with Pydantic error |
| `GET /api/trades — list with pagination` | 200 + paginated response shape |
| `GET /api/trades — filter by status` | 200 + only matching trades |
| `GET /api/trades/{id} — exists` | 200 + correct trade |
| `GET /api/trades/{id} — not found` | 404 with standard detail |
| `PATCH /api/trades/{id} — valid update` | 200 + updated fields |
| `PATCH /api/trades/{id} — past editable` | 409 with conflict detail |
| `DELETE /api/trades/{id}` | 204 + is_active=False in DB |
| `POST /api/trades/{id}/close` | 200 + status=closed, exit fields set |
| `POST /api/accounts` | 201 + name unique enforced |
| `GET /api/markets` | 200 + 7 seeded rows |
| `GET /api/brokers/{id} — not found` | 404 with standard detail |

**Error response schema tests** (for every relevant endpoint):

| Test | What it verifies |
|------|-----------------|
| `404 response shape` | `{"detail": "..."}` |
| `409 response shape` | `{"detail": "..."}` |
| `422 response shape` | `{"detail": [{"type": "...", "loc": [...], "msg": "...", "input": ...}]}` |
| `pagination response shape` | `{"items": [], "total": N, "page": N, "page_size": N, "pages": N}` |

---

## 10. Traceability

### 10.1 Endpoint ↔ Proposal BR Mapping

| Endpoint | BR-07 | BR-08 | BR-09 | BR-10 | BR-12 | BR-17 | BR-29 |
|----------|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|:-----:|
| `POST /api/trades` | ✓ | ✓ | ✓ | ✓ | — | — | — |
| `PATCH /api/trades/{id}` | ✓ | ✓ | ✓ | — | ✓ | — | — |
| `POST /api/trades/{id}/close` | — | — | — | ✓ | — | — | — |
| `DELETE /api/trades/{id}` | — | — | — | — | — | — | ✓ |
| `POST /api/brokers` | — | — | — | — | — | ✓ | — |

### 10.2 Proposal Capability ↔ Spec Section

| Proposal Capability | Spec Section |
|---------------------|-------------|
| `trade-crud` | §1.1, §3.1, §6.2, §7.1 |
| `account-crud` | §1.2, §3.2, §6.3, §7.2 |
| `asset-crud` | §1.3, §3.3, §6.4, §7.3 |
| `catalog-read` | §1.4, §3.4, §6.5, §7.4 |

### 10.3 NFR ↔ Proposal Risk

| NFR | Proposal Risk Mitigation |
|-----|------------------------|
| NFR-03 (isolated test DB) | "Isolated DB per test run — seed via Alembic or inline inserts" |
| NFR-06 (no schema changes) | "Soft-delete semantics: is_active=False only, status unchanged" |

### 10.4 Test Coverage Matrix

| Layer | Success Path Tests | Violation Path Tests | Total |
|-------|-------------------|---------------------|-------|
| Repository | 6 | 4 | 10 |
| Service | 7 | 11 | 18 |
| Endpoint Integration | 9 | 6 | 15 |
| **Total** | **22** | **21** | **43** |

---

## 11. Routing Architecture

The endpoint router structure SHALL use a single `router.py` per module with sub-routers for entity groups:

```
app/modules/trading_journal/
├── __init__.py
├── router.py           ← mounts sub-routers: trades, accounts, assets, catalogs
├── dependencies.py     ← service DI for trading_journal entities
├── service.py          ← TradeService (can also be separate files per entity)
```

All catalog endpoints (`/api/markets`, `/api/market-sessions`, `/api/timeframes`, `/api/brokers`) SHALL be mounted under the `trading_journal` module as read-only sub-routers.

Account and Asset endpoints SHALL also be mounted under `trading_journal` for MVP coherence — all domain entities share a single journal context.

```
trading_journal/router.py
├── router_trades = APIRouter(prefix="/api/trades", tags=["Trades"])
├── router_accounts = APIRouter(prefix="/api/accounts", tags=["Accounts"])
├── router_assets = APIRouter(prefix="/api/assets", tags=["Assets"])
├── router_catalogs = APIRouter(prefix="/api", tags=["Catalogs"])
│   ├── /markets
│   ├── /market-sessions
│   ├── /timeframes
│   └── /brokers
└── router.include_router(sub_router) for each
```
