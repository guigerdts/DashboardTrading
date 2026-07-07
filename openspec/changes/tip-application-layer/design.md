# Design: TIP Application Layer (MVP)

**Change**: `tip-application-layer` — Repository, Unit of Work, Service, DTO, and REST endpoint layers on top of the existing domain model. No DB schema changes.

---

## 1. Architecture Overview

### 1.1 Three-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  API Layer (FastAPI Endpoints)                              │
│  - Parse request → call service → return response           │
│  - Zero business logic                                      │
│  - Pydantic DTOs for request/response                       │
│  - Auth (future)                                            │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                              │
│  - All business rule enforcement                            │
│  - BR-07, BR-08, BR-09, BR-10, BR-12, BR-17, BR-29         │
│  - Orchestrates repositories via UnitOfWork                 │
│  - Structured logging                                       │
│  - Raises domain exceptions                                 │
├─────────────────────────────────────────────────────────────┤
│  Repository Layer                                           │
│  - Pure CRUD — zero business logic                          │
│  - Typed queries with filter parameters                     │
│  - Returns ORM model instances                              │
│  - No logging, no commit()                                  │
├─────────────────────────────────────────────────────────────┤
│  Domain Model (SQLAlchemy ORM)                              │
│  - 21 tables, 29 BRs, existing — NOT modified               │
│  - Trade, Account, Asset, Market, Broker, ...               │
│  - TimestampMixin, SoftDeleteMixin, Base                    │
│  - AsyncSession throughout                                  │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Request Data Flow — Happy Path (POST /api/trades)

```
Client
  │  POST /api/trades  { account_id, asset_id, direction, ... }
  ▼
FastAPI receives request
  │  1. Pydantic TradeCreate validates format/types → 422 if malformed
  │  2. get_db() creates AsyncSession
  │  3. get_uow() wraps session → yields UnitOfWork
  │  4. get_trade_service() creates TradeService(uow)
  ▼
TradeService.create(dto)
  │  1. _validate_sl_tp() — BR-07, BR-08, BR-09
  │  2. _validate_exit_consistency() — BR-10
  │  3. Construct Trade ORM instance from dto
  │  4. uow.trades.add(trade) → session.add() + flush() → gets id
  │  5. Return Trade ORM instance
  ▼
FastAPI Depends cleanup
  │  get_uow resumes after yield
  │  6. uow.commit() → session.commit()
  │  7. Response: TradeResponse (Pydantic from_attributes)
  ▼
Client ← 201 { id, account_id, direction, entry_price, ... }
```

### 1.3 Error Scenario Flow (BR-12 — past editable window)

```
Client
  │  PATCH /api/trades/42  { commission: 5.0 }
  ▼
FastAPI
  │  Pydantic validates → OK
  ▼
TradeService.update(42, dto)
  │  1. uow.trades.get(42) → Trade or None
  │  2. trade is None → raise NotFoundError
  │  3. trade.editable_until is past → raise BusinessRuleError
  ▼
  BusinessRuleError("Trade 42 past editable window ...")
  │  422 status_code
  ▼
get_uow.__aexit__ rolls back session
  │  await session.rollback()
  ▼
Global exception handler (app_error_handler)
  │  Returns JSONResponse(status_code=422, detail={...})
  ▼
Client ← 422 { "detail": [{ "type": "business_rule_violation", ... }] }
```

### 1.4 Layer Decision Table

| Concern | Layer | Why |
|---------|-------|-----|
| Format validation (required fields, types, gt/ge) | Pydantic DTO | FastAPI-native, auto-docs, zero code |
| Business rule enforcement (SL/TP side, edit window) | Service | Testable in isolation, independent of transport |
| Data access (get, list, add, update) | Repository | Swappable backend, no leaky abstractions |
| Transaction commit/rollback | UoW (via Depends) | Request-scoped, auto-rollback on error |
| HTTP status codes | Exception handler | Centralized, consistent error format |
| Pagination computation | Repository (count) + Service (pages) | Count at DB level, pages computed in service |
| Soft-delete | Service | Sets `is_active=False`, does NOT delete from DB |
| OpenAPI docs | FastAPI (auto) | Schema-driven, zero additional code |
| ORM→DTO mapping | Service return + Pydantic `from_attributes` | Boundary conversion, never expose ORM to client |

---

## 2. Directory Structure

```
backend/app/
├── core/                          NEW — Shared transverse concerns
│   ├── __init__.py                NEW
│   ├── config.py                  EXISTING (moved from app/config.py)
│   └── exceptions.py             NEW — AppError, NotFoundError, ConflictError, BusinessRuleError
├── db/                            NEW — Database access layer
│   ├── __init__.py                NEW
│   ├── database.py                EXISTING (moved from app/database.py)
│   ├── unit_of_work.py            NEW — UnitOfWork, repository accessors
│   └── dependencies.py            MODIFIED — add get_uow(), get_*_service()
├── models/                        EXISTING — 21 tables, no changes
├── modules/
│   ├── shared/                    NEW — Shared base abstractions
│   │   ├── __init__.py            NEW
│   │   ├── base.py                NEW — AbstractRepository[T], SqlAlchemyRepository[T]
│   │   └── pagination.py          NEW — PaginationParams, PaginatedResponse, MessageResponse, filter DTOs
│   ├── catalogs/                  NEW — Markets, MarketSessions, Timeframes, Brokers
│   │   ├── __init__.py            NEW
│   │   ├── router.py              NEW — read-only GET + broker CRUD
│   │   ├── service.py             NEW — CatalogService, BrokerService
│   │   ├── repository.py          NEW — MarketRepository, MarketSessionRepository, TimeframeRepository, BrokerRepository
│   │   └── schemas.py             NEW — MarketResponse, MarketSessionResponse, TimeframeResponse, BrokerCreate, BrokerResponse
│   ├── accounts/                  NEW — Account management
│   │   ├── __init__.py            NEW
│   │   ├── router.py              NEW — CRUD endpoints
│   │   ├── service.py             NEW — AccountService
│   │   ├── repository.py          NEW — AccountRepository
│   │   └── schemas.py             NEW — AccountCreate, AccountUpdate, AccountResponse, AccountFilters
│   ├── assets/                    NEW — Asset management
│   │   ├── __init__.py            NEW
│   │   ├── router.py              NEW — CRUD endpoints
│   │   ├── service.py             NEW — AssetService
│   │   ├── repository.py          NEW — AssetRepository
│   │   └── schemas.py             NEW — AssetCreate, AssetUpdate, AssetResponse, AssetFilters
│   └── trades/                    NEW — Trade management
│       ├── __init__.py            NEW
│       ├── router.py              NEW — CRUD + close endpoint
│       ├── service.py             NEW — TradeService
│       ├── repository.py          NEW — TradeRepository
│       └── schemas.py             NEW — TradeCreate, TradeUpdate, TradeClose, TradeResponse, TradeFilters
└── main.py                        MODIFIED — register global exception handlers, module discovery
```

**Total**: ~28 new files, 1 modified file (`app/main.py`), 0 removed files.  
Each module is self-contained with its own router/service/repository/schemas. Shared abstractions live in `app/modules/shared/`. The `discover_modules()` auto-loader in `main.py` discovers `app/modules/*/router.py` — no manual registration needed.

---

## 3. Generic Repository Base

### 3.1 AbstractRepository[T]

```python
# backend/app/modules/shared/base.py

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")

class AbstractRepository(ABC, Generic[T]):
    """Typed repository contract — one per entity."""

    @abstractmethod
    async def add(self, entity: T) -> T: ...

    @abstractmethod
    async def get(self, id: int) -> T | None: ...

    @abstractmethod
    async def list(self, **filters) -> tuple[list[T], int]: ...

    @abstractmethod
    async def update(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, entity: T) -> None: ...

    @abstractmethod
    async def exists(self, **criteria) -> bool: ...
```

### 3.2 SqlAlchemyRepository[T]

```python
class SqlAlchemyRepository(AbstractRepository[T]):
    """SQLAlchemy implementation shared by all entity repositories.

    - All methods are async (AsyncSession throughout)
    - No commit() — UnitOfWork owns the transaction boundary
    - session.flush() after add so caller gets the generated id
    """

    def __init__(self, session: AsyncSession, entity_class: type[T]):
        self._session = session
        self._entity = entity_class

    async def add(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get(self, id: int) -> T | None:
        return await self._session.get(self._entity, id)

    async def update(self, entity: T) -> T:
        await self._session.merge(entity)
        return entity

    async def delete(self, entity: T) -> None:
        await self._session.delete(entity)

    async def exists(self, **criteria) -> bool:
        stmt = select(exists().where(
            *[getattr(self._entity, k) == v for k, v in criteria.items()]
        ))
        result = await self._session.execute(stmt)
        return result.scalar()

    async def count(self, *filters) -> int:
        stmt = select(func.count()).select_from(self._entity)
        if filters:
            stmt = stmt.where(*filters)
        result = await self._session.execute(stmt)
        return result.scalar()
```

---

## 4. Concrete Repositories

Each entity's repository lives in its module's `repository.py`:

| Module | File | Repository |
|--------|------|------------|
| `trades` | `app/modules/trades/repository.py` | `TradeRepository` |
| `accounts` | `app/modules/accounts/repository.py` | `AccountRepository` |
| `assets` | `app/modules/assets/repository.py` | `AssetRepository` |
| `catalogs` | `app/modules/catalogs/repository.py` | `MarketRepository`, `MarketSessionRepository`, `TimeframeRepository`, `BrokerRepository` |

### 4.1 TradeRepository

```python
# backend/app/modules/trades/repository.py

class TradeRepository(SqlAlchemyRepository[Trade]):

    def __init__(self, session: AsyncSession):
        super().__init__(session, Trade)

    async def list(
        self,
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
    ) -> tuple[list[Trade], int]:
        """Compose WHERE clauses dynamically. Default ordering: entry_datetime DESC."""
        where_clauses: list = [Trade.is_active == (1 if is_active else 0)]

        if status:
            where_clauses.append(Trade.status == status)
        if direction:
            where_clauses.append(Trade.direction == direction)
        if account_id:
            where_clauses.append(Trade.account_id == account_id)
        if asset_id:
            where_clauses.append(Trade.asset_id == asset_id)
        if date_from:
            where_clauses.append(Trade.entry_datetime >= date_from)
        if date_to:
            where_clauses.append(Trade.entry_datetime <= date_to)
        if search:
            where_clauses.append(Trade.notes_override.ilike(f"%{search}%"))

        base_stmt = select(Trade).where(*where_clauses)

        # Count
        count_stmt = select(func.count()).select_from(Trade).where(*where_clauses)
        total = (await self._session.execute(count_stmt)).scalar()

        # Paginated query
        stmt = (
            base_stmt
            .order_by(Trade.entry_datetime.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        items = list((await self._session.execute(stmt)).scalars().all())

        return items, total
```

### 4.2 AccountRepository

```python
class AccountRepository(SqlAlchemyRepository[Account]):

    def __init__(self, session: AsyncSession):
        super().__init__(session, Account)

    async def get_by_name(self, name: str) -> Account | None:
        stmt = select(Account).where(Account.name == name)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        status: str | None = None,
        search: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Account], int]:
        where = [Account.is_active == (1 if is_active else 0)]
        if status:
            where.append(Account.status == status)
        if search:
            where.append(Account.name.ilike(f"%{search}%"))

        total = (await self._session.execute(
            select(func.count()).select_from(Account).where(*where)
        )).scalar()

        items = list((await self._session.execute(
            select(Account).where(*where)
            .order_by(Account.name)
            .limit(page_size).offset((page - 1) * page_size)
        )).scalars().all())

        return items, total
```

### 4.3 AssetRepository

```python
class AssetRepository(SqlAlchemyRepository[Asset]):

    def __init__(self, session: AsyncSession):
        super().__init__(session, Asset)

    async def get_by_symbol_market(self, symbol: str, market_id: int) -> Asset | None:
        stmt = select(Asset).where(
            Asset.symbol == symbol,
            Asset.market_id == market_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        symbol: str | None = None,
        market_id: int | None = None,
        search: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Asset], int]:
        where = [Asset.is_active == (1 if is_active else 0)]
        if symbol:
            where.append(Asset.symbol == symbol)
        if market_id:
            where.append(Asset.market_id == market_id)
        if search:
            where.append(Asset.name.ilike(f"%{search}%"))

        # When symbol is provided without market_id, return ALL assets with that symbol
        # (global search per design decision)

        total = (await self._session.execute(
            select(func.count()).select_from(Asset).where(*where)
        )).scalar()

        items = list((await self._session.execute(
            select(Asset).where(*where)
            .order_by(Asset.symbol, Asset.market_id)
            .limit(page_size).offset((page - 1) * page_size)
        )).scalars().all())

        return items, total
```

### 4.4 Catalog Repositories

All follow the same pattern — simple `list_all()` and `get()`:

```python
class MarketRepository(SqlAlchemyRepository[Market]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Market)

    async def list_all(self) -> list[Market]:
        stmt = select(Market).order_by(Market.name)
        return list((await self._session.execute(stmt)).scalars().all())

class BrokerRepository(SqlAlchemyRepository[Broker]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Broker)

    async def list_all(self) -> list[Broker]:
        stmt = select(Broker).where(Broker.is_active == 1).order_by(Broker.name)
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_by_name(self, name: str) -> Broker | None:
        stmt = select(Broker).where(Broker.name == name)
        return (await self._session.execute(stmt)).scalar_one_or_none()
```

**MarketSessionRepository** and **TimeframeRepository** mirror `MarketRepository`.

---

## 5. Unit of Work

### 5.1 UnitOfWork Class

```python
# backend/app/db/unit_of_work.py

class UnitOfWork:
    """Single transaction boundary per request.

    Exposes all repositories as lazy-init properties.
    Commit/rollback lifecycle managed by FastAPI Depends generator,
    NOT by this class directly.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._trades: TradeRepository | None = None
        self._accounts: AccountRepository | None = None
        self._assets: AssetRepository | None = None
        self._markets: MarketRepository | None = None
        self._market_sessions: MarketSessionRepository | None = None
        self._timeframes: TimeframeRepository | None = None
        self._brokers: BrokerRepository | None = None

    @property
    def trades(self) -> TradeRepository:
        if self._trades is None:
            self._trades = TradeRepository(self._session)
        return self._trades

    @property
    def accounts(self) -> AccountRepository:
        if self._accounts is None:
            self._accounts = AccountRepository(self._session)
        return self._accounts

    # ... same lazy-init pattern for assets, markets, market_sessions,
    #     timeframes, brokers

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
```

### 5.2 DI Integration (FastAPI Depends)

```python
# backend/app/db/dependencies.py

from app.db.unit_of_work import UnitOfWork
from app.modules.trades.service import TradeService
from app.modules.trades.repository import TradeRepository
from app.modules.accounts.service import AccountService
from app.modules.assets.service import AssetService
from app.modules.catalogs.service import BrokerService, CatalogService

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """AsyncSession per request — base dependency."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_uow(db: AsyncSession = Depends(get_db)) -> AsyncGenerator[UnitOfWork, None]:
    """UnitOfWork per request — commit on success, rollback on exception.

    FastAPI calls next() to enter the generator, then resumes after yield
    when the request completes. If the request handler raises, FastAPI
    calls athrow() and the except block catches it.
    """
    uow = UnitOfWork(db)
    try:
        yield uow
        await uow.commit()
    except Exception:
        await uow.rollback()
        raise
```

### 5.3 Service DI

```python
async def get_trade_service(uow: UnitOfWork = Depends(get_uow)) -> TradeService:
    return TradeService(uow)

async def get_account_service(uow: UnitOfWork = Depends(get_uow)) -> AccountService:
    return AccountService(uow)

async def get_asset_service(uow: UnitOfWork = Depends(get_uow)) -> AssetService:
    return AssetService(uow)

async def get_broker_service(uow: UnitOfWork = Depends(get_uow)) -> BrokerService:
    return BrokerService(uow)
```

**Important**: Each service call creates its own UoW. If you chain service calls in one request, each gets a separate UoW + session. For MVP this is fine — each endpoint creates exactly one UoW per request via Depends. If cross-entity operations are needed later, the caller can inject the same UoW into multiple services.

---

## 6. Service Contracts

All services follow the same pattern: receive UoW, enforce BRs, raise domain exceptions, return ORM instances (mapped to DTOs by Pydantic in the response).

### 6.1 TradeService

```python
class TradeService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.logger = logging.getLogger(__name__)

    async def create(self, dto: TradeCreate) -> Trade:
        """Create a trade. Enforces BR-07, BR-08, BR-09, BR-10."""
        self._validate_sl_tp(
            direction=dto.direction,
            entry_price=dto.entry_price,
            stop_loss=dto.stop_loss,
            take_profit=dto.take_profit,
        )
        self._validate_exit_consistency(
            status=dto.status,
            exit_price=dto.exit_price,
            exit_datetime=dto.exit_datetime,
        )

        trade = Trade(
            account_id=dto.account_id,
            asset_id=dto.asset_id,
            direction=dto.direction,
            status=dto.status,
            entry_price=dto.entry_price,
            quantity=dto.quantity,
            entry_datetime=dto.entry_datetime.isoformat(),
            exit_price=dto.exit_price,
            exit_datetime=dto.exit_datetime.isoformat() if dto.exit_datetime else None,
            stop_loss=dto.stop_loss,
            take_profit=dto.take_profit,
            position_size=dto.position_size,
            commission=dto.commission or 0,
            swap_fees=dto.swap_fees or 0,
            risk_amount=dto.risk_amount,
            broker_id=dto.broker_id,
            market_session_id=dto.market_session_id,
            timeframe_id=dto.timeframe_id,
            notes_override=dto.notes_override,
            editable_until=_compute_editable_until(dto.status, dto.entry_datetime),
        )

        await self.uow.trades.add(trade)
        self.logger.info("Created trade id=%d status=%s", trade.id, trade.status)
        return trade

    async def get(self, id: int) -> Trade:
        """Get trade by ID. Raises NotFoundError if missing."""
        trade = await self.uow.trades.get(id)
        if trade is None:
            raise NotFoundError("Trade", id)
        return trade

    async def list(self, filters: TradeFilters) -> tuple[list[Trade], int]:
        """List trades with filters + pagination."""
        return await self.uow.trades.list(
            status=filters.status,
            direction=filters.direction,
            account_id=filters.account_id,
            asset_id=filters.asset_id,
            date_from=filters.date_from,
            date_to=filters.date_to,
            search=filters.search,
            is_active=filters.is_active,
            page=filters.page,
            page_size=filters.page_size,
        )

    async def update(self, id: int, dto: TradeUpdate) -> Trade:
        """Update trade fields. Enforces BR-12, BR-07, BR-08, BR-09."""
        trade = await self.get(id)
        self._validate_editable(trade)

        # Apply changes
        update_data = dto.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(trade, field, value)

        # Re-validate if SL/TP/direction changed
        if any(f in update_data for f in ("stop_loss", "take_profit", "direction", "entry_price")):
            self._validate_sl_tp(
                direction=trade.direction,
                entry_price=trade.entry_price,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
            )

        trade.updated_at = _utcnow()
        self.logger.info("Updated trade id=%d fields=%s", id, set(update_data.keys()))
        return trade

    async def close(self, id: int, dto: TradeClose) -> Trade:
        """Close a trade. Enforces BR-10. Sets editable_until."""
        trade = await self.get(id)
        if trade.status == "closed":
            raise BusinessRuleError(f"Trade with id {id} is already closed")

        trade.exit_price = dto.exit_price
        trade.exit_datetime = dto.exit_datetime.isoformat()
        trade.status = "closed"
        trade.editable_until = _compute_editable_until("closed")
        trade.updated_at = _utcnow()

        self.logger.info("Closed trade id=%d exit_price=%s", id, dto.exit_price)
        return trade

    async def soft_delete(self, id: int) -> None:
        """BR-29: Set is_active=False, do NOT change status."""
        trade = await self.get(id)
        trade.is_active = 0  # SQLite boolean
        trade.updated_at = _utcnow()
        self.logger.info("Soft-deleted trade id=%d", id)

    # --- Private validation methods ---

    def _validate_sl_tp(
        self, direction: str, entry_price: float,
        stop_loss: float | None, take_profit: float | None,
    ) -> None:
        """BR-07, BR-08, BR-09."""
        if stop_loss is not None:
            if direction == "long" and stop_loss >= entry_price:
                raise BusinessRuleError(
                    "Stop loss must be below entry price for long trades "
                    f"(entry: {entry_price}, sl: {stop_loss})"
                )
            if direction == "short" and stop_loss <= entry_price:
                raise BusinessRuleError(
                    "Stop loss must be above entry price for short trades "
                    f"(entry: {entry_price}, sl: {stop_loss})"
                )
        if take_profit is not None:
            if direction == "long" and take_profit <= entry_price:
                raise BusinessRuleError(
                    "Take profit must be above entry price for long trades "
                    f"(entry: {entry_price}, tp: {take_profit})"
                )
            if direction == "short" and take_profit >= entry_price:
                raise BusinessRuleError(
                    "Take profit must be below entry price for short trades "
                    f"(entry: {entry_price}, tp: {take_profit})"
                )
        if stop_loss is not None and take_profit is not None:
            sl_below = stop_loss < entry_price
            tp_below = take_profit < entry_price
            if sl_below == tp_below:
                raise BusinessRuleError(
                    "Stop loss and take profit must be on opposite sides of entry price "
                    f"(entry: {entry_price}, sl: {stop_loss}, tp: {take_profit})"
                )

    def _validate_exit_consistency(
        self, status: str, exit_price: float | None, exit_datetime: str | None,
    ) -> None:
        """BR-10: both NULL or both set. If closed, both required."""
        if status == "closed":
            if exit_price is None or exit_datetime is None:
                raise BusinessRuleError(
                    "exit_price and exit_datetime are required when status is 'closed'"
                )
        else:  # open
            if exit_price is not None or exit_datetime is not None:
                raise BusinessRuleError(
                    "exit_price and exit_datetime must be null when status is 'open'"
                )

    def _validate_editable(self, trade: Trade) -> None:
        """BR-12: 30-day soft-lock."""
        if trade.editable_until is not None:
            if datetime.now(UTC).isoformat() > trade.editable_until:
                raise BusinessRuleError(
                    f"Trade with id {trade.id} is past its editable window "
                    f"(editable_until: {trade.editable_until})"
                )
```

**Utility**:

```python
def _compute_editable_until(status: str, entry_datetime: datetime | None = None) -> str | None:
    """BR-12: 30 days from entry_datetime (create) or now (close)."""
    if status == "open":
        return None
    base = entry_datetime or datetime.now(UTC)
    from_ = base if isinstance(base, datetime) else datetime.fromisoformat(base)
    return (from_ + timedelta(days=30)).isoformat()
```

### 6.2 AccountService

```python
class AccountService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create(self, dto: AccountCreate) -> Account:
        existing = await self.uow.accounts.get_by_name(dto.name)
        if existing:
            raise ConflictError(f"Account with name '{dto.name}' already exists")
        account = Account(
            name=dto.name,
            broker=dto.broker,
            account_type=dto.account_type,
            base_currency=dto.base_currency or "USD",
            status=dto.status or "active",
        )
        await self.uow.accounts.add(account)
        return account

    async def get(self, id: int) -> Account:
        account = await self.uow.accounts.get(id)
        if account is None:
            raise NotFoundError("Account", id)
        return account

    async def list(self, filters: AccountFilters) -> tuple[list[Account], int]:
        return await self.uow.accounts.list(
            status=filters.status,
            search=filters.search,
            is_active=filters.is_active,
            page=filters.page,
            page_size=filters.page_size,
        )

    async def update(self, id: int, dto: AccountUpdate) -> Account:
        account = await self.get(id)
        update_data = dto.model_dump(exclude_unset=True)
        # Check name uniqueness if name changed
        if "name" in update_data and update_data["name"] != account.name:
            existing = await self.uow.accounts.get_by_name(update_data["name"])
            if existing:
                raise ConflictError(f"Account with name '{update_data['name']}' already exists")
        for field, value in update_data.items():
            setattr(account, field, value)
        account.updated_at = _utcnow()
        return account

    async def soft_delete(self, id: int) -> None:
        account = await self.get(id)
        account.is_active = 0
        account.updated_at = _utcnow()
```

### 6.3 AssetService

```python
class AssetService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create(self, dto: AssetCreate) -> Asset:
        # Validate market exists
        market = await self.uow.markets.get(dto.market_id)
        if market is None:
            raise BusinessRuleError(f"Market with id {dto.market_id} does not exist")
        # Check symbol+market uniqueness
        existing = await self.uow.assets.get_by_symbol_market(dto.symbol, dto.market_id)
        if existing:
            raise ConflictError(
                f"Asset with symbol '{dto.symbol}' and market_id {dto.market_id} already exists"
            )
        asset = Asset(symbol=dto.symbol, name=dto.name, market_id=dto.market_id)
        await self.uow.assets.add(asset)
        return asset

    async def get(self, id: int) -> Asset:
        asset = await self.uow.assets.get(id)
        if asset is None:
            raise NotFoundError("Asset", id)
        return asset

    async def list(self, filters: AssetFilters) -> tuple[list[Asset], int]:
        return await self.uow.assets.list(
            symbol=filters.symbol,
            market_id=filters.market_id,
            search=filters.search,
            is_active=filters.is_active,
            page=filters.page,
            page_size=filters.page_size,
        )

    async def update(self, id: int, dto: AssetUpdate) -> Asset:
        asset = await self.get(id)
        update_data = dto.model_dump(exclude_unset=True)
        # Re-validate uniqueness if symbol or market_id changed
        if "symbol" in update_data or "market_id" in update_data:
            new_symbol = update_data.get("symbol", asset.symbol)
            new_market_id = update_data.get("market_id", asset.market_id)
            existing = await self.uow.assets.get_by_symbol_market(new_symbol, new_market_id)
            if existing and existing.id != id:
                raise ConflictError(
                    f"Asset with symbol '{new_symbol}' and market_id {new_market_id} already exists"
                )
        if "market_id" in update_data:
            market = await self.uow.markets.get(update_data["market_id"])
            if market is None:
                raise BusinessRuleError(f"Market with id {update_data['market_id']} does not exist")
        for field, value in update_data.items():
            setattr(asset, field, value)
        asset.updated_at = _utcnow()
        return asset

    async def soft_delete(self, id: int) -> None:
        asset = await self.get(id)
        asset.is_active = 0
        asset.updated_at = _utcnow()
```

### 6.4 BrokerService

```python
class BrokerService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def create(self, dto: BrokerCreate) -> Broker:
        # BR-17: suggest uniqueness — check existing, allow creation
        existing = await self.uow.brokers.get_by_name(dto.name)
        if existing:
            self.logger.warning("Broker with name '%s' already exists (BR-17)", dto.name)
        broker = Broker(name=dto.name)
        await self.uow.brokers.add(broker)
        return broker

    async def get(self, id: int) -> Broker:
        broker = await self.uow.brokers.get(id)
        if broker is None:
            raise NotFoundError("Broker", id)
        return broker

    async def list_all(self) -> list[Broker]:
        return await self.uow.brokers.list_all()
```

---

## 7. DTO / Schema Specifications

### 7.1 Common Schemas (Shared Module)

```python
# backend/app/modules/shared/pagination.py

from pydantic import BaseModel, Field
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginationParams(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int

class MessageResponse(BaseModel):
    message: str
    detail: str | None = None
```

### 7.2 Trade Schemas

```python
# backend/app/modules/trades/schemas.py

from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class TradeCreate(BaseModel):
    account_id: int
    asset_id: int
    direction: Literal["long", "short"]
    status: Literal["open", "closed"]
    entry_price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    entry_datetime: datetime
    exit_price: float | None = None
    exit_datetime: datetime | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    position_size: float | None = Field(default=None, ge=0)
    commission: float = Field(default=0, ge=0)
    swap_fees: float = Field(default=0, ge=0)
    risk_amount: float | None = None
    broker_id: int | None = None
    market_session_id: int | None = None
    timeframe_id: int | None = None
    notes_override: str | None = None

class TradeUpdate(BaseModel):
    entry_price: float | None = Field(default=None, gt=0)
    quantity: float | None = Field(default=None, gt=0)
    entry_datetime: datetime | None = None
    exit_price: float | None = None
    exit_datetime: datetime | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    position_size: float | None = Field(default=None, ge=0)
    commission: float | None = Field(default=None, ge=0)
    swap_fees: float | None = Field(default=None, ge=0)
    risk_amount: float | None = None
    direction: Literal["long", "short"] | None = None
    notes_override: str | None = None
    broker_id: int | None = None
    market_session_id: int | None = None
    timeframe_id: int | None = None

class TradeClose(BaseModel):
    exit_price: float = Field(gt=0)
    exit_datetime: datetime

class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account_id: int
    asset_id: int
    direction: str
    status: str
    entry_price: float
    quantity: float
    entry_datetime: str
    exit_price: float | None = None
    exit_datetime: str | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    position_size: float | None = None
    commission: float = 0
    swap_fees: float = 0
    risk_amount: float | None = None
    broker_id: int | None = None
    market_session_id: int | None = None
    timeframe_id: int | None = None
    editable_until: str | None = None
    notes_override: str | None = None
    is_active: bool
    created_at: str
    updated_at: str | None = None
```

### 7.3 Account Schemas

```python
# backend/app/modules/accounts/schemas.py

class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    broker: str | None = None
    account_type: str | None = None
    base_currency: str = "USD"
    status: Literal["active", "inactive"] = "active"

class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    broker: str | None = None
    account_type: str | None = None
    base_currency: str | None = None
    status: Literal["active", "inactive"] | None = None

class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    broker: str | None = None
    account_type: str | None = None
    base_currency: str
    status: str
    is_active: bool
    created_at: str
    updated_at: str | None = None
```

### 7.4 Asset Schemas

```python
# backend/app/modules/assets/schemas.py

class AssetCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=50)
    name: str | None = None
    market_id: int

class AssetUpdate(BaseModel):
    symbol: str | None = Field(default=None, min_length=1)
    name: str | None = None
    market_id: int | None = None

class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    symbol: str
    name: str | None = None
    market_id: int
    is_active: bool
    created_at: str
    updated_at: str | None = None
```

### 7.5 Catalog Schemas

```python
# backend/app/modules/catalogs/schemas.py

class MarketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: str

class MarketSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: str

class TimeframeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: str

class BrokerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)

class BrokerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_active: bool
    created_at: str
    updated_at: str | None = None
```

---

## 8. Exception Definitions

```python
# backend/app/core/exceptions.py

class AppError(Exception):
    """Base application error — caught by global exception handler."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found → 404."""

    def __init__(self, entity: str, id: int):
        super().__init__(
            f"{entity} with id {id} not found",
            status_code=404,
        )


class ConflictError(AppError):
    """Resource conflict / duplicate → 409."""

    def __init__(self, message: str):
        super().__init__(message, status_code=409)


class BusinessRuleError(AppError):
    """Business rule violation → 422 (matches FastAPI validation error style).

    Rendered as a Pydantic-style error array for consistency with FastAPI's
    422 format.
    """

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message, status_code=422)
```

### Global Exception Handler

```python
# In backend/app/main.py

from app.core.exceptions import AppError, BusinessRuleError

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
    # ... middleware, routers ...

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        if isinstance(exc, BusinessRuleError):
            # Return Pydantic-style 422 error array
            detail = [{
                "type": "business_rule_violation",
                "loc": ["body", exc.field] if exc.field else ["body"],
                "msg": exc.message,
                "input": None,
            }]
            return JSONResponse(status_code=422, content={"detail": detail})
        # 404, 409 → simple detail string
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    return app
```

---

## 9. DI Wiring

Providers live in `app/db/dependencies.py` using **late imports** to avoid import failures from Foundation before module packages exist. Each module's router injects its service via `Depends(provider_function)`, keeping the API layer decoupled from implementation and enabling `app.dependency_overrides` in tests.

```python
# backend/app/db/dependencies.py — MODIFIED

from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import async_session_factory
from app.db.unit_of_work import UnitOfWork

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_uow(db: AsyncSession = Depends(get_db)) -> AsyncGenerator[UnitOfWork, None]:
    uow = UnitOfWork(db)
    try:
        yield uow
        await uow.commit()
    except Exception:
        await uow.rollback()
        raise


# ─── Service Providers (late imports — Foundation-safe) ───────────
# Late imports defer package resolution to runtime, so app/db/dependencies.py
# can be imported from Foundation before any module package exists.
# This also enables app.dependency_overrides[get_trade_service] in tests.

async def get_trade_service(uow: UnitOfWork = Depends(get_uow)) -> "TradeService":
    from app.modules.trades.service import TradeService
    return TradeService(uow)

async def get_account_service(uow: UnitOfWork = Depends(get_uow)) -> "AccountService":
    from app.modules.accounts.service import AccountService
    return AccountService(uow)

async def get_asset_service(uow: UnitOfWork = Depends(get_uow)) -> "AssetService":
    from app.modules.assets.service import AssetService
    return AssetService(uow)

async def get_broker_service(uow: UnitOfWork = Depends(get_uow)) -> "BrokerService":
    from app.modules.catalogs.service import BrokerService
    return BrokerService(uow)
```

### 9.1 Foundation Quality Criteria

These invariants apply to all Foundation code and must be verified in Foundation tests:

| # | Criterion | Enforced by | Verification |
|---|-----------|-------------|-------------|
| QC-01 | **UnitOfWork is sole session owner** — repositories never call `commit()`, `rollback()`, or `close()`. Only `flush()` when the caller needs an ID after `add()`. | `SqlAlchemyRepository` only exposes `flush()` via `add()`; no commit/rollback/close methods on repos | Test: repo calls `add()` → session not committed; after test rollback, entity not persisted |
| QC-02 | **Repositories know nothing about FastAPI** — they depend solely on `AsyncSession` and domain model types. No `Depends`, `Request`, `Response`, or HTTP imports in any repository file. | `AbstractRepository[T]` takes `AsyncSession`; concrete repos extend with SQLAlchemy queries only | Code review: grep for `fastapi`, `Depends`, `Request`, `Response` in `app/modules/*/repository.py` and `app/modules/shared/base.py` |
| QC-03 | **Providers are pure construction** — `get_trade_service(uow)` only builds `TradeService(uow)`. Zero business logic, zero validation, zero decision-making in any provider function. | Provider body is a single `return ServiceClass(uow)` or equivalent | Code review: every `get_*_service()` body is one line: `from ... import Service; return Service(uow)` |
| QC-04 | **One AsyncSession per request** — `get_db()` yields a session; `get_uow()` wraps it. The same session is shared by all repositories in that UoW instance. | `get_db()` creates the session, `get_uow()` receives it, all repo properties on UoW reference `self._session` | Test: create UoW, access `.trades` and `.accounts`, both return repos with same `id(self._session)` |

See §12.4 for Foundation-specific test cases.

---

## 10. Endpoint Router Structure

Per the module-per-feature architecture, each module owns its own `router.py`. The `discover_modules()` auto-loader in `main.py` discovers `app/modules/*/router.py` and mounts them. Each module router is self-contained — imports its own service, schemas, and DI from within the module.

### 10.1 Trades Router

```python
# backend/app/modules/trades/router.py

from fastapi import APIRouter, Depends
from app.db.dependencies import get_uow, get_trade_service
from app.modules.shared.pagination import PaginatedResponse
from app.modules.trades.schemas import (
    TradeCreate, TradeUpdate, TradeClose, TradeResponse, TradeFilters,
)
from app.modules.trades.service import TradeService

router = APIRouter(prefix="/api/trades", tags=["Trades"])


@router.post("/", response_model=TradeResponse, status_code=201)
async def create_trade(
    dto: TradeCreate,
    svc: TradeService = Depends(get_trade_service),
):
    return await svc.create(dto)


@router.get("/", response_model=PaginatedResponse[TradeResponse])
async def list_trades(
    filters: TradeFilters = Depends(),
    svc: TradeService = Depends(get_trade_service),
):
    items, total = await svc.list(filters)
    pages = max(1, (total + filters.page_size - 1) // filters.page_size)
    return PaginatedResponse(
        items=items, total=total,
        page=filters.page, page_size=filters.page_size, pages=pages,
    )


@router.get("/{id}", response_model=TradeResponse)
async def get_trade(
    id: int,
    svc: TradeService = Depends(get_trade_service),
):
    return await svc.get(id)


@router.patch("/{id}", response_model=TradeResponse)
async def update_trade(
    id: int,
    dto: TradeUpdate,
    svc: TradeService = Depends(get_trade_service),
):
    return await svc.update(id, dto)


@router.delete("/{id}", status_code=204)
async def delete_trade(
    id: int,
    svc: TradeService = Depends(get_trade_service),
):
    await svc.soft_delete(id)


@router.post("/{id}/close", response_model=TradeResponse)
async def close_trade(
    id: int,
    dto: TradeClose,
    svc: TradeService = Depends(get_trade_service),
):
    return await svc.close(id, dto)
```

### 10.2 Accounts Router

```python
# backend/app/modules/accounts/router.py

from fastapi import APIRouter, Depends
from app.db.dependencies import get_account_service
from app.modules.shared.pagination import PaginatedResponse
from app.modules.accounts.schemas import (
    AccountCreate, AccountUpdate, AccountResponse, AccountFilters,
)
from app.modules.accounts.service import AccountService

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


@router.post("/", response_model=AccountResponse, status_code=201)
async def create_account(
    dto: AccountCreate,
    svc: AccountService = Depends(get_account_service),
):
    return await svc.create(dto)


@router.get("/", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    filters: AccountFilters = Depends(),
    svc: AccountService = Depends(get_account_service),
):
    items, total = await svc.list(filters)
    pages = max(1, (total + filters.page_size - 1) // filters.page_size)
    return PaginatedResponse(items=items, total=total, page=filters.page, page_size=filters.page_size, pages=pages)


@router.get("/{id}", response_model=AccountResponse)
async def get_account(
    id: int,
    svc: AccountService = Depends(get_account_service),
):
    return await svc.get(id)


@router.patch("/{id}", response_model=AccountResponse)
async def update_account(
    id: int,
    dto: AccountUpdate,
    svc: AccountService = Depends(get_account_service),
):
    return await svc.update(id, dto)


@router.delete("/{id}", status_code=204)
async def delete_account(
    id: int,
    svc: AccountService = Depends(get_account_service),
):
    await svc.soft_delete(id)
```

### 10.3 Assets Router

```python
# backend/app/modules/assets/router.py

from fastapi import APIRouter, Depends
from app.db.dependencies import get_asset_service
from app.modules.shared.pagination import PaginatedResponse
from app.modules.assets.schemas import (
    AssetCreate, AssetUpdate, AssetResponse, AssetFilters,
)
from app.modules.assets.service import AssetService

router = APIRouter(prefix="/api/assets", tags=["Assets"])


@router.post("/", response_model=AssetResponse, status_code=201)
async def create_asset(
    dto: AssetCreate,
    svc: AssetService = Depends(get_asset_service),
):
    return await svc.create(dto)


@router.get("/", response_model=PaginatedResponse[AssetResponse])
async def list_assets(
    filters: AssetFilters = Depends(),
    svc: AssetService = Depends(get_asset_service),
):
    items, total = await svc.list(filters)
    pages = max(1, (total + filters.page_size - 1) // filters.page_size)
    return PaginatedResponse(items=items, total=total, page=filters.page, page_size=filters.page_size, pages=pages)


@router.get("/{id}", response_model=AssetResponse)
async def get_asset(
    id: int,
    svc: AssetService = Depends(get_asset_service),
):
    return await svc.get(id)


@router.patch("/{id}", response_model=AssetResponse)
async def update_asset(
    id: int,
    dto: AssetUpdate,
    svc: AssetService = Depends(get_asset_service),
):
    return await svc.update(id, dto)


@router.delete("/{id}", status_code=204)
async def delete_asset(
    id: int,
    svc: AssetService = Depends(get_asset_service),
):
    await svc.soft_delete(id)
```

### 10.4 Catalogs Router

```python
# backend/app/modules/catalogs/router.py

from fastapi import APIRouter, Depends
from app.db.dependencies import get_uow, get_broker_service
from app.modules.catalogs.schemas import (
    MarketResponse, MarketSessionResponse, TimeframeResponse,
    BrokerCreate, BrokerResponse,
)
from app.modules.catalogs.service import BrokerService, CatalogService

router = APIRouter(prefix="/api", tags=["Catalogs"])


@router.get("/markets", response_model=list[MarketResponse])
async def list_markets(uow=Depends(get_uow)):
    svc = CatalogService(uow)
    return await svc.list_markets()


@router.get("/market-sessions", response_model=list[MarketSessionResponse])
async def list_market_sessions(uow=Depends(get_uow)):
    svc = CatalogService(uow)
    return await svc.list_market_sessions()


@router.get("/timeframes", response_model=list[TimeframeResponse])
async def list_timeframes(uow=Depends(get_uow)):
    svc = CatalogService(uow)
    return await svc.list_timeframes()


@router.get("/brokers", response_model=list[BrokerResponse])
async def list_brokers(
    svc: BrokerService = Depends(get_broker_service),
):
    return await svc.list_all()


@router.get("/brokers/{id}", response_model=BrokerResponse)
async def get_broker(
    id: int,
    svc: BrokerService = Depends(get_broker_service),
):
    return await svc.get(id)


@router.post("/brokers", response_model=BrokerResponse, status_code=201)
async def create_broker(
    dto: BrokerCreate,
    svc: BrokerService = Depends(get_broker_service),
):
    return await svc.create(dto)
```

### 10.5 Auto-Discovery

No manual mounting needed. The `discover_modules()` function in `app/main.py` scans `app/modules/*/router.py` and includes each router. Each module's `router = APIRouter(prefix="/api/...")` defines its own prefix — no wrapping sub-router needed.

```python
# In app/main.py (pseudo)
from app.modules.trades.router import router as trades_router
from app.modules.accounts.router import router as accounts_router
from app.modules.assets.router import router as assets_router
from app.modules.catalogs.router import router as catalogs_router

app.include_router(trades_router)
app.include_router(accounts_router)
app.include_router(assets_router)
app.include_router(catalogs_router)
```

---

## 11. Pagination

### Filter DTOs with Pagination

Each list endpoint has a dedicated filter DTO extending `PaginationParams`:

Filter DTOs live in each module's `schemas.py` and extend `PaginationParams` from the shared module:

```python
# app/modules/shared/pagination.py — PaginationParams, PaginatedResponse
# app/modules/trades/schemas.py — TradeFilters(PaginationParams)
# app/modules/accounts/schemas.py — AccountFilters(PaginationParams)
# app/modules/assets/schemas.py — AssetFilters(PaginationParams)

class TradeFilters(PaginationParams):
    status: Literal["open", "closed"] | None = None
    direction: Literal["long", "short"] | None = None
    account_id: int | None = None
    asset_id: int | None = None
    date_from: str | None = None  # ISO 8601
    date_to: str | None = None
    search: str | None = None
    is_active: bool = True

class AccountFilters(PaginationParams):
    status: Literal["active", "inactive"] | None = None
    search: str | None = None
    is_active: bool = True

class AssetFilters(PaginationParams):
    symbol: str | None = None
    market_id: int | None = None
    search: str | None = None
    is_active: bool = True
```

### Paginated Response

```python
# app/modules/shared/pagination.py

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int  # computed: ceil(total / page_size)
```

Computed in the endpoint (not the service) — the service returns `(items, total)`, the endpoint computes `pages`.

---

## 12. Test Architecture

### 12.1 Fixtures (`tests/conftest.py`)

```python
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from app.models.base import Base
from app.main import create_app
from app.db.dependencies import get_db

@pytest.fixture(scope="session")
def event_loop():
    """Session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """In-memory SQLite engine — isolated per test run."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(async_engine):
    """Transaction-per-test session — rollback after each test."""
    async with async_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        await conn.rollback()

@pytest_asyncio.fixture
async def client(db_session):
    """FastAPI test client with overridden DB dependency."""
    app = create_app()

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def uow(db_session):
    """UnitOfWork for direct service/repository tests."""
    from app.db.unit_of_work import UnitOfWork
    uow = UnitOfWork(db_session)
    yield uow
    await uow.rollback()
```

### 12.2 Test Matrix

| Layer | File | Tests | Focus |
|-------|------|-------|-------|
| Repository | `tests/modules/trades/test_repository.py` | 12 | CRUD, filters, pagination, soft-delete |
| Repository | `tests/modules/accounts/test_repository.py` | 8 | CRUD, name uniqueness, status filter |
| Repository | `tests/modules/assets/test_repository.py` | 8 | CRUD, symbol+market filter, uniqueness |
| Repository | `tests/modules/catalogs/test_repository.py` | 8 | list_all, get for each catalog entity |
| Service | `tests/modules/trades/test_service.py` | 14 | BR-07/08/09/10/12/29, all edge cases |
| Service | `tests/modules/accounts/test_service.py` | 6 | Create duplicate, soft-delete |
| Service | `tests/modules/assets/test_service.py` | 6 | Create duplicate, missing market |
| Integration | `tests/modules/trades/test_endpoints.py` | 12 | Full HTTP round-trips, error codes |
| Integration | `tests/modules/accounts/test_endpoints.py` | 6 | Full HTTP round-trips |
| Integration | `tests/modules/assets/test_endpoints.py` | 6 | Full HTTP round-trips |
| Integration | `tests/modules/catalogs/test_endpoints.py` | 8 | Read-only GET, broker create |
| **Total** | | **86** | |

### 12.3 Key Test Patterns

**Repository test**:
```python
async def test_add_and_get_trade(uow):
    trade = Trade(account_id=1, asset_id=1, direction="long", status="open",
                  entry_price=1.0, quantity=100, entry_datetime="2026-01-01T00:00:00Z")
    await uow.trades.add(trade)
    result = await uow.trades.get(trade.id)
    assert result is not None
    assert result.entry_price == 1.0
```

**Service test**:
```python
async def test_create_long_trade_invalid_sl(uow):
    svc = TradeService(uow)
    dto = TradeCreate(account_id=1, asset_id=1, direction="long", status="open",
                      entry_price=1.0, quantity=100, entry_datetime=datetime.now(UTC),
                      stop_loss=1.1)
    with pytest.raises(BusinessRuleError):
        await svc.create(dto)
```

**Integration test**:
```python
async def test_create_trade_success(client):
    response = await client.post("/api/trades", json={
        "account_id": 1, "asset_id": 1, "direction": "long", "status": "open",
        "entry_price": 1.0, "quantity": 1000,
        "entry_datetime": "2026-07-06T15:00:00Z",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["direction"] == "long"
    assert data["status"] == "open"
```

---

## 13. Traceability Matrix

### 13.1 Endpoint → BR → Service Method

| Endpoint | BR | Service Method | Module | Status |
|----------|----|----------------|--------|--------|
| `POST /api/trades` | BR-07, BR-08, BR-09, BR-10 | `TradeService.create()` | `trades` | ✓ |
| `PATCH /api/trades/{id}` | BR-12, BR-07, BR-08, BR-09 | `TradeService.update()` | `trades` | ✓ |
| `POST /api/trades/{id}/close` | BR-10 | `TradeService.close()` | `trades` | ✓ |
| `DELETE /api/trades/{id}` | BR-29 | `TradeService.soft_delete()` | `trades` | ✓ |
| `POST /api/accounts` | BR-26 (DB UNIQUE) | `AccountService.create()` | `accounts` | ✓ |
| `POST /api/assets` | BR-16 (DB UNIQUE) | `AssetService.create()` | `assets` | ✓ |
| `POST /api/brokers` | BR-17 | `BrokerService.create()` | `catalogs` | ✓ |
| `GET /api/trades` | — | `TradeService.list()` | `trades` | ✓ |
| `GET /api/accounts` | — | `AccountService.list()` | `accounts` | ✓ |
| `GET /api/assets` | — | `AssetService.list()` | `assets` | ✓ |
| `GET /api/markets` | — | `CatalogService.list_markets()` | `catalogs` | ✓ |
| `GET /api/brokers` | — | `BrokerService.list_all()` | `catalogs` | ✓ |
| `GET /api/brokers/{id}` | — | `BrokerService.get()` | `catalogs` | ✓ |

### 13.2 Repository → Entity Table

| Repository | Module | Entity | Table |
|------------|--------|--------|-------|
| `TradeRepository` | `trades/repository.py` | `Trade` | `trades` |
| `AccountRepository` | `accounts/repository.py` | `Account` | `accounts` |
| `AssetRepository` | `assets/repository.py` | `Asset` | `assets` |
| `MarketRepository` | `catalogs/repository.py` | `Market` | `markets` |
| `MarketSessionRepository` | `catalogs/repository.py` | `MarketSession` | `market_sessions` |
| `TimeframeRepository` | `catalogs/repository.py` | `Timeframe` | `timeframes` |
| `BrokerRepository` | `catalogs/repository.py` | `Broker` | `brokers` |

### 13.3 DTO → Entity Mapping

| DTO | Entity | Type | Module | Notes |
|-----|--------|------|--------|-------|
| `TradeCreate` | → `Trade` | Create | `trades/schemas.py` | Required fields + conditional exit |
| `TradeUpdate` | → `Trade` | Update | `trades/schemas.py` | All optional |
| `TradeClose` | → `Trade` | Update | `trades/schemas.py` | Exit fields only |
| `TradeResponse` | ← `Trade` | Response | `trades/schemas.py` | `from_attributes=True` |
| `AccountCreate` | → `Account` | Create | `accounts/schemas.py` | Name unique check |
| `AccountUpdate` | → `Account` | Update | `accounts/schemas.py` | All optional |
| `AccountResponse` | ← `Account` | Response | `accounts/schemas.py` | `from_attributes=True` |
| `AssetCreate` | → `Asset` | Create | `assets/schemas.py` | symbol+market unique check |
| `AssetUpdate` | → `Asset` | Update | `assets/schemas.py` | All optional |
| `AssetResponse` | ← `Asset` | Response | `assets/schemas.py` | `from_attributes=True` |
| `MarketResponse` | ← `Market` | Response | `catalogs/schemas.py` | Read-only |
| `BrokerCreate` | → `Broker` | Create | `catalogs/schemas.py` | BR-17 suggested unique |
| `BrokerResponse` | ← `Broker` | Response | `catalogs/schemas.py` | Read+write |

### 13.4 NFR Coverage

| NFR | Design Section | Implementation |
|-----|---------------|----------------|
| NFR-01 (API-first) | §10 Endpoints | FastAPI auto OpenAPI, Pydantic schemas |
| NFR-02 (Async) | §3-6, §9-10 | `async def` everywhere, `AsyncSession` |
| NFR-03 (Isolated test DB) | §12.1 | In-memory SQLite, `Base.metadata.create_all` |
| NFR-04 (Standardized errors) | §8 | `AppError` → global handler in `app/core/exceptions.py` |
| NFR-05 (Pagination) | §11 | `PaginatedResponse` in `app/modules/shared/pagination.py` |
| NFR-06 (No schema changes) | Entire design | No model/table modifications |
| NFR-07 (DTO separation) | §7 | Distinct Create/Update/Response per module's `schemas.py` |
| NFR-08 (Zero logic in repos) | §3-4 | Pure CRUD, typed queries only |
| NFR-09 (Single service layer) | §6 | All BRs in per-module services |
| NFR-10 (One UoW per request) | §5.2 | `get_uow()` Depends in `app/db/dependencies.py` |

---

## 14. Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **UoW + Depends lifecycle mismatch**: Service catches exception but UoW already committed | Low | UoW commit happens in Depends cleanup AFTER yield, not in service. Service raises → Depends catches → rollback. This is the standard FastAPI pattern. |
| **is_active mapping (int ↔ bool)**: Model stores `is_active` as `int` (SQLite), Pydantic uses `bool` | Low | Pydantic `from_attributes=True` coerces `0/1` to `False/True`. The `TradeResponse.is_active: bool` works correctly. Repository queries use `Trade.is_active == (1 if is_active else 0)`. |
| **Float precision for monetary values**: SQLite REAL is IEEE 64-bit float | Low | Acceptable for MVP. PPTA: max 15 significant figures for trade quantities under 10^9 units. If precision issues surface, migrate to TEXT-encoded Decimal in a future phase. |
| **Session leak on Depends exception**: `get_db()` safely closes session in `finally` | None | Pattern already in existing `dependencies.py`. The `finally` block guarantees cleanup. |
| **Catalog service DI overhead**: Catalog endpoints need simple services but current pattern creates full UoW | Low | Lightweight services + direct UoW injection for catalog reads. Acceptable overhead for MVP — each catalog call creates one async session. |
| **Each module router must define its own prefix**: `trades/router.py` uses `prefix="/api/trades"`, `accounts/router.py` uses `prefix="/api/accounts"`, etc. No sub-router wrapping needed — each is independently discoverable by `discover_modules()`. | Low | Module-per-feature eliminates the prefix nesting issue. Each module's `router = APIRouter(prefix="/api/...")` defines its own path. `discover_modules()` in `main.py` scans `app/modules/*/router.py` and includes each router independently. No prefix collision risk. |

---

## 15. Migration / Rollout

**No data migration required**. This is purely an application-layer addition — no schema changes, no columns added, no tables created. The domain model already exists with all 21 tables.

**Rollback**: Revert the stacked PR commits in reverse order. All new files are additive — removing them leaves the domain model intact.

**Deployment sequence**:
1. PR #1: Foundation — `app/core/`, `app/db/`, `app/modules/shared/` (base repo, UoW, DI, exceptions). No endpoints exposed.
2. PR #2: Catalogs module — `app/modules/catalogs/` (read-only GET + broker CRUD). First live endpoints.
3. PR #3: Trades module — `app/modules/trades/` (full trade CRUD with BR enforcement).
4. PR #4: Accounts + Assets modules — `app/modules/accounts/`, `app/modules/assets/`.

Each PR merges to `main` independently. Module-per-feature means no blocking dependencies between modules after the foundation PR.

---

## Open Questions

- [✓] **`is_active` type in Response DTOs**: Use `bool` (Pydantic coerces `int` 0/1 to `False/True`). **Resolution**: Use `bool` — it's the correct semantic type; Pydantic handles coercion transparently.
- [✓] **Catalog service pattern**: Single `CatalogService` for read-only entities (markets, sessions, timeframes); separate `BrokerService` for broker CRUD. Both in `app/modules/catalogs/service.py`. **Resolution**: Two services in the catalogs module — `CatalogService` for read-only, `BrokerService` for full CRUD.
- [✓] **Module-per-feature vs single module**: Per-module architecture was chosen. See AD-05.
- [ ] **UoW direct injection vs per-service DI**: Each module router uses `get_uow()` directly and instantiates services inline (`svc = TradeService(uow)`). This avoids per-service DI boilerplate. Confirm this doesn't break request isolation. **Proposed resolution**: Works because each request gets its own UoW via `Depends(get_uow)` — the generator lifecycle ensures no session sharing across requests.

---

## Architecture Decisions Log

### AD-01: UoW Lifecycle via FastAPI Depends (not context manager)

**Choice**: Commit/rollback managed by the `get_uow()` FastAPI dependency generator, not by a context manager in the service.

**Alternatives**: 
1. UoW as context manager used inside service methods (`async with UnitOfWork(session):`)
2. UoW Depends with `__aenter__`/`__aexit__`

**Rationale**: FastAPI's `Depends` generator lifecycle (`yield` + cleanup) naturally maps to request-scoped transactions. The service never calls `commit()`/`rollback()` — it raises exceptions on BR violations, and the Depends generator handles the rest. This eliminates the risk of a service forgetting to commit or rolling back when it shouldn't.

### AD-02: Business Rule Errors as 422 (not 400 or 409)

**Choice**: BR violations return HTTP 422 with Pydantic-style error array.

**Alternatives**: 400 (generic bad request), 409 (conflict — not semantically correct for SL/TP validation)

**Rationale**: FastAPI's default 422 for Pydantic validation errors sets the convention. Business rule violations are semantically validation errors — the request body is syntactically valid (right types, required fields present) but semantically invalid (SL on wrong side of entry). Using 422 keeps validation errors uniform. The error body uses Pydantic's array format for consistency.

### AD-03: Pydantic `from_attributes` for Response DTOs (not manual mapping)

**Choice**: Use `model_config = ConfigDict(from_attributes=True)` on all Response DTOs.

**Alternatives**: Manual `TradeResponse.model_validate(trade)` with explicit field mapping.

**Rationale**: `from_attributes=True` automatically reads ORM attributes by name. Since fields in Response DTOs mirror the ORM model attributes exactly, this eliminates boilerplate. The mapping happens at the boundary (when FastAPI serializes the response), keeping the service layer returning ORM instances.

### AD-04: Services Return ORM Instances (not DTOs)

**Choice**: Service methods return SQLAlchemy ORM instances. DTO conversion happens at the endpoint level via Pydantic.

**Alternatives**: Services return DTOs. ORM→DTO mapping in the service.

**Rationale**: Returning ORM instances keeps services testable against the real domain model. DTOs are a transport concern — they belong at the boundary. The endpoint declares `response_model=TradeResponse`, and FastAPI handles the conversion. If we need to map to a different response format (e.g., GraphQL), the service doesn't change.

### AD-05: Module-per-Feature Architecture

**Choice**: Each entity domain lives in its own module under `app/modules/{trades,accounts,assets,catalogs}/`, each with its own `router.py`, `service.py`, `repository.py`, and `schemas.py`.

**Alternatives**: All endpoints in a single `trading_journal` module with sub-routers. Global layers (`app/repositories/`, `app/services/`, `app/schemas/`).

**Rationale**: Module-per-feature gives clear ownership boundaries — a developer or AI agent working on trades only touches `app/modules/trades/`. The existing `discover_modules()` already scans `app/modules/*/router.py`, so no module discovery changes are needed. Each module is independently testable, importable, and can be extracted into its own service later without structural changes. Cross-cutting concerns (base repository, pagination DTOs) live in `app/modules/shared/` and `app/db/`.

---

## 16. Task Segmentation Rules

These rules govern how the change is split into implementation tasks. They ensure each PR is vertically functional, independently reviewable, and maintains traceability.

### 16.1 Granularity: One Task = One Complete Module

**No mixed tasks.** Each task delivers one complete module including ALL its layers:

| Module | Contents |
|--------|----------|
| `Foundation` | `app/core/exceptions.py`, `app/db/unit_of_work.py`, `app/db/dependencies.py`, `app/modules/shared/base.py`, `app/modules/shared/pagination.py` |
| `Catalogs` | `app/modules/catalogs/__init__.py`, `app/modules/catalogs/repository.py`, `app/modules/catalogs/service.py`, `app/modules/catalogs/schemas.py`, `app/modules/catalogs/router.py`, `tests/modules/catalogs/test_repository.py`, `tests/modules/catalogs/test_endpoints.py` |
| `Trades` | `app/modules/trades/__init__.py`, `app/modules/trades/repository.py`, `app/modules/trades/service.py`, `app/modules/trades/schemas.py`, `app/modules/trades/router.py`, `tests/modules/trades/test_repository.py`, `tests/modules/trades/test_service.py`, `tests/modules/trades/test_endpoints.py` |
| `Accounts` | `app/modules/accounts/__init__.py`, `app/modules/accounts/repository.py`, `app/modules/accounts/service.py`, `app/modules/accounts/schemas.py`, `app/modules/accounts/router.py`, `tests/modules/accounts/test_repository.py`, `tests/modules/accounts/test_service.py`, `tests/modules/accounts/test_endpoints.py` |
| `Assets` | `app/modules/assets/__init__.py`, `app/modules/assets/repository.py`, `app/modules/assets/service.py`, `app/modules/assets/schemas.py`, `app/modules/assets/router.py`, `tests/modules/assets/test_repository.py`, `tests/modules/assets/test_service.py`, `tests/modules/assets/test_endpoints.py` |
| `Integration` | `app/main.py` (router registration), `tests/conftest.py`, integration tests, OpenAPI docs verification |

A task NEVER mixes modules (e.g., no "repos + accounts + assets" in one task).

### 16.2 Vertical Functionality

Each PR must be **vertically functional** — it adds a slice that works end-to-end:

- Repository (read/write from DB)
- Service (enforce BRs)
- Schemas (validate request/response at boundary)
- Router (expose via HTTP)
- Tests (verify the full slice)
- Router registration (wire into the app)

This means each PR can be tested independently: `pytest tests/modules/trades/` runs ALL trade tests with no dependency on other modules.

### 16.3 Task Entry Requirements

Every task in `tasks.md` MUST include:

| Field | Required | Example |
|-------|----------|---------|
| **Files** | Yes — exhaustive list | `app/modules/trades/repository.py`, `app/modules/trades/service.py`, ... |
| **Dependencies** | Yes — task IDs this depends on | `TASK-001 Foundation` |
| **Business Rules** | Yes — BR numbers implemented | BR-07, BR-08, BR-09, BR-10, BR-12, BR-29 |
| **Acceptance Criteria** | Yes — verifiable, testable | "POST /api/trades returns 201 with TradeResponse body" |
| **Required Tests** | Yes — which tests files and what they cover | `tests/modules/trades/test_service.py` — 14 tests covering all BR edge cases |
| **Line Estimate** | Yes — target <400-500 lines per PR | `~380 lines` |

### 16.4 PR Size Budget

- Each PR should stay **under 400–500 lines changed** when possible.
- If a module exceeds 500 lines, split by concern within the same module boundary (e.g., separate PR for service tests vs endpoint tests).
- The Foundation PR is the exception — it's infrastructure, not a feature.

### 16.5 Dependency Order

```
Foundation (no deps)
  └─ Catalogs (deps: Foundation)
  └─ Trades (deps: Foundation)     ← parallelizable with Catalogs
  └─ Accounts (deps: Foundation)   ← parallelizable with Catalogs/Trades
  └─ Assets (deps: Foundation)     ← parallelizable with Catalogs/Trades/Accounts
      └─ Integration (deps: all of the above)
```

Foundation must be first. Feature modules are independent of each other. Integration is last.

---

## 17. File Change Summary

### New Files (27 total)

| File | Module | Description |
|------|--------|-------------|
| `app/core/__init__.py` | — | Package init |
| `app/core/exceptions.py` | — | `AppError`, `NotFoundError`, `ConflictError`, `BusinessRuleError` |
| `app/db/__init__.py` | — | Package init |
| `app/db/unit_of_work.py` | — | `UnitOfWork` with lazy-init repo properties |
| `app/db/dependencies.py` | — | `get_db()`, `get_uow()` Depends generators |
| `app/modules/shared/__init__.py` | `shared` | Package init |
| `app/modules/shared/base.py` | `shared` | `AbstractRepository[T]`, `SqlAlchemyRepository[T]` |
| `app/modules/shared/pagination.py` | `shared` | `PaginationParams`, `PaginatedResponse`, `MessageResponse` |
| `app/modules/trades/__init__.py` | `trades` | Package init |
| `app/modules/trades/router.py` | `trades` | Trade CRUD + close endpoints |
| `app/modules/trades/service.py` | `trades` | `TradeService` with all BR enforcement |
| `app/modules/trades/repository.py` | `trades` | `TradeRepository` with filtered `list()` |
| `app/modules/trades/schemas.py` | `trades` | `TradeCreate`, `TradeUpdate`, `TradeClose`, `TradeResponse`, `TradeFilters` |
| `app/modules/accounts/__init__.py` | `accounts` | Package init |
| `app/modules/accounts/router.py` | `accounts` | Account CRUD endpoints |
| `app/modules/accounts/service.py` | `accounts` | `AccountService` |
| `app/modules/accounts/repository.py` | `accounts` | `AccountRepository` with `get_by_name()` |
| `app/modules/accounts/schemas.py` | `accounts` | `AccountCreate`, `AccountUpdate`, `AccountResponse`, `AccountFilters` |
| `app/modules/assets/__init__.py` | `assets` | Package init |
| `app/modules/assets/router.py` | `assets` | Asset CRUD endpoints |
| `app/modules/assets/service.py` | `assets` | `AssetService` |
| `app/modules/assets/repository.py` | `assets` | `AssetRepository` with `get_by_symbol_market()` |
| `app/modules/assets/schemas.py` | `assets` | `AssetCreate`, `AssetUpdate`, `AssetResponse`, `AssetFilters` |
| `app/modules/catalogs/__init__.py` | `catalogs` | Package init |
| `app/modules/catalogs/router.py` | `catalogs` | Read-only GET + broker CRUD |
| `app/modules/catalogs/service.py` | `catalogs` | `CatalogService`, `BrokerService` |
| `app/modules/catalogs/repository.py` | `catalogs` | `MarketRepository`, `MarketSessionRepository`, `TimeframeRepository`, `BrokerRepository` |
| `app/modules/catalogs/schemas.py` | `catalogs` | `MarketResponse`, `MarketSessionResponse`, `TimeframeResponse`, `BrokerCreate`, `BrokerResponse` |

### Modified Files (1)

| File | Changes |
|------|---------|
| `app/main.py` | Register `app_error_handler` exception handler, import per-module routers |

### Removed Files (0)

No existing files are removed. The architecture is additive.

### Test Files (11)

| File | Module | Focus |
|------|--------|-------|
| `tests/conftest.py` | — | Async fixtures, in-memory engine, test client |
| `tests/modules/trades/test_repository.py` | `trades` | CRUD, filters, pagination, soft-delete |
| `tests/modules/trades/test_service.py` | `trades` | BR-07/08/09/10/12/29, all edge cases |
| `tests/modules/trades/test_endpoints.py` | `trades` | Full HTTP round-trips, error codes |
| `tests/modules/accounts/test_repository.py` | `accounts` | CRUD, name uniqueness, status filter |
| `tests/modules/accounts/test_service.py` | `accounts` | Create duplicate, soft-delete |
| `tests/modules/accounts/test_endpoints.py` | `accounts` | Full HTTP round-trips |
| `tests/modules/assets/test_repository.py` | `assets` | CRUD, symbol+market filter, uniqueness |
| `tests/modules/assets/test_service.py` | `assets` | Create duplicate, missing market |
| `tests/modules/assets/test_endpoints.py` | `assets` | Full HTTP round-trips |
| `tests/modules/catalogs/test_repository.py` | `catalogs` | list_all, get for each catalog entity |
| `tests/modules/catalogs/test_endpoints.py` | `catalogs` | Read-only GET, broker create |

### Deployment Sequence (Updated)

Module-per-feature allows independent PRs by module:

1. **PR #1: Foundation** — `app/core/`, `app/db/`, `app/modules/shared/` (base repo, UoW, DI, exceptions). No endpoints exposed.
2. **PR #2: Catalogs** — `app/modules/catalogs/` (read-only GET + broker CRUD). First live endpoints.
3. **PR #3: Trades** — `app/modules/trades/` (full trade CRUD with BR enforcement).
4. **PR #4: Accounts + Assets** — `app/modules/accounts/`, `app/modules/assets/`.

Each PR is independently reviewable and merges to `main` without breaking the existing app.
