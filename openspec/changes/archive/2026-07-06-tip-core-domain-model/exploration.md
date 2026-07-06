# Exploration: TIP Core Domain Model — Entities, Relationships, Business Rules, ER Model, and SQLite Physical Data Model

## Current State

Fase 1 (Infrastructure) is complete. The monorepo has:

- **Backend**: FastAPI app factory with `create_app()`, async SQLite engine + session factory (WAL mode), Alembic configured with empty `versions/`, 10 module skeletons under `app/modules/` (dashboard, trading_journal, analytics, risk_management, psychology, strategies, setups, screenshot_library, error_management, settings). Each module contains only `__init__.py`, `router.py` (with `@router.get("/") → raise NotImplementedError`), and a `README.md`. Zero SQLAlchemy models, zero Pydantic schemas, zero services, zero repositories. CORS configured for `localhost:5173`.

- **Frontend**: Vite + React (JS, no TypeScript), landing page with navigation, 10 route stubs, Tailwind CSS configured.

- **Database**: Configurable via `TIP_DB_PATH` (default `data/tip.db`). Async engine via `sqlalchemy[asyncio]` + `aiosqlite`. WAL mode enabled on startup.

- **Constraints in effect (C1–C6)**:
  - C1 (Modularity): modules are fully decoupled islands.
  - C2 (Database First): no domain entities or models yet.
  - C3/C4: only structural scaffolding exists.

No domain code exists. This exploration defines the complete entity model that will drive Fase 2.

## Affected Areas

- `backend/app/models/` — **new**: SQLAlchemy declarative models directory (to be created in sdd-apply)
- `backend/app/schemas/` — **new**: Pydantic schemas for each entity (to be created in sdd-apply)
- `backend/app/repositories/` — **new**: data access layer (to be created in sdd-apply)
- `backend/app/modules/trading_journal/` — core domain logic for Trade CRUD
- `backend/app/modules/analytics/` — derived metrics computed from trades
- `backend/app/modules/risk_management/` — position sizing and risk rules
- `backend/app/modules/psychology/` — emotion tracking tied to trades
- `backend/app/modules/strategies/` — strategy definitions
- `backend/app/modules/setups/` — setup templates
- `backend/app/modules/screenshot_library/` — screenshot storage linked to trades
- `backend/app/modules/error_management/` — mistake recording linked to trades
- `backend/app/database.py` — add `Base = declarative_base()` and foreign-key pragma
- `backend/alembic/env.py` — wire `target_metadata` to models' `Base.metadata`
- `backend/alembic/versions/` — **new**: initial migration revisions
- `backend/pyproject.toml` — may need `pydantic` (already a FastAPI dependency) for schemas

---

## Stage 2.1 — Domain Entities

### Canonical Entity List

The system has **19 entities** organized by domain module.

#### Core Trading Entities (trading_journal)

| # | Entity | Description | Module |
|---|--------|-------------|--------|
| 1 | **Trade** | Central entity — a single trading operation (opened and closed). NEVER physically deleted — only archived or marked inactive (BR-29). | trading_journal |
| 2 | **Account** | A trading account. Each trade belongs to exactly one account. Contains broker, account type, base currency, status. | trading_journal |
| 3 | **Asset** | A financial instrument traded (EUR/USD, BTC/USD, AAPL, ES1!, etc.) | trading_journal |
| 4 | **Market** | The market/asset class (forex, crypto, stocks, futures, indices, commodities) | trading_journal |
| 5 | **Broker** | The intermediary that executed the trade | trading_journal |
| 6 | **MarketSession** | Market session context (Asian, London, New York, Pre-Market, etc.) | trading_journal |
| 7 | **Timeframe** | Chart timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN) | trading_journal |

#### User Work Session

| # | Entity | Description | Module |
|---|--------|-------------|--------|
| 8 | **TradingSession** | A user's work session that groups multiple trades conducted in the same period. Distinct from MarketSession. | trading_journal |

#### Strategy & Setup Entities

| # | Entity | Description | Module |
|---|--------|-------------|--------|
| 9 | **Strategy** | A trading plan with rules, parameters, and risk settings | strategies |
| 10 | **Setup** | A specific chart pattern or entry configuration (Bull Flag, Engulfing, RSI Divergence, etc.) | setups |

#### Psychology Entities

| # | Entity | Description | Module |
|---|--------|-------------|--------|
| 11 | **Emotion** | An emotional state (fear, greed, confidence, anxiety, euphoria, frustration, etc.) | psychology |
| 12 | **EmotionEntry** | Records a specific emotion felt during a trade with intensity + timing context | psychology |

#### Review & Notes

| # | Entity | Description | Module |
|---|--------|-------------|--------|
| 13 | **Note** | Quick inline note attached to a trade (short, journal-style) | trading_journal |
| 14 | **TradeReview** | Structured post-trade review — separate from quick notes. Contains detailed analysis, lessons learned,评分. | trading_journal |

#### Cross-Cutting Entities

| # | Entity | Description | Module |
|---|--------|-------------|--------|
| 15 | **Tag** | Free-form label for categorizing/filtering trades | trading_journal (cross-cutting) |
| 16 | **Attachment** | Generic file attachment (image, PDF, document, video reference). Replaces narrower Screenshot concept. | screenshot_library |
| 17 | **Mistake** | A trading error category (FOMO, revenge trading, cutting winners early, etc.) | error_management |
| 18 | **MistakeEntry** | Records a specific mistake committed in a trade | error_management |

#### Risk Entities

| # | Entity | Description | Module |
|---|--------|-------------|--------|
| 19 | **RiskProfile** | Risk configuration used for a trade — profile/preset only. NO stored metrics or calculated values. All metrics computed dynamically. | risk_management |

### Non-Stored / Derived Concepts

These are NOT persisted as tables. They are computed on-the-fly:

| Concept | Source | Computation |
|---------|--------|-------------|
| **Performance Metrics** (win rate, Sharpe, Sortino, max drawdown, profit factor, expectancy) | All closed trades | Computed by analytics module |
| **Equity Curve** | Closed trades sorted by exit_date | Computed ordered projection |
| **Trade Statistics** (avg R:R, avg win, avg loss, largest win/loss) | Closed trades | Computed aggregate |
| **PnL** (per trade) | entry_price, exit_price, quantity, direction, commission, swap | Computed field (can be cached) |
| **R:R Ratio** | entry_price, stop_loss, take_profit | Computed |
| **R Multiple** | actual PnL / initial risk | Computed |
| **Concentration** (per asset/market) | open trades grouped by asset | Computed |
| **Session Stats** (performance per session) | Trades grouped by session | Computed |

### Entities Explicitly Excluded

| Concept | Exclusion Reason |
|---------|-----------------|
| `User` | Single-user application (offline-first, personal journal). Multi-user support is a future concern. |
| `BacktestResult` | Backtesting is a future fase. Strategy analysis starts with journaled trades. |
| `TradingPlan` | A plan IS a strategy in this domain. No separate entity needed. |
| `PriceData` (OHLCV bars) | Market data ingestion is a separate future fase. TIP starts with trade journaling. |
| `Alert` / `Notification` | Cross-cutting concern, not domain data. Handled by infrastructure. |
| `Screenshot` (as separate) | Replaced by `Attachment` — supports images, PDFs, documents, videos. Screenshots are attachments with `type='image'`. |

---

## Stage 2.2 — Relationships

### Entity Relationship Map

```
┌────────────┐
│  Account   │
│  (master)  │
└─────┬──────┘
      │ 1:N
      │
┌─────▼──────┐     N:1     ┌──────────┐
│   Trade    │──────────────│  Asset   │
│  (master)  │     N:1     ├──────────┤
│            │──────────────│  Market  │  (via Asset)
│            │     N:1     ├──────────┤
│            │──────────────│  Broker  │
│            │     N:1     ├──────────┤
│            │──────────────│MarketSession│
│            │     N:1     ├──────────┤
│            │──────────────│Timeframe │
│            │     N:1     ├──────────┤
│            │──────────────│Strategy  │
│            │     N:1     ├──────────┤
│            │──────────────│  Setup   │
│            │     N:1     ├──────────┤
│            │──────────────│RiskProfile│
│            │     N:1     ├──────────┤
│            │──────────────│TradingSession│
│            │              └──────────┘
│            │
│     1:N    │──┐
│  Emotions  │  ├──── EmotionEntry (trade_id, emotion_id, intensity, timing)
│     1:N    │──┘
│            │
│     1:N    │──┐
│  Mistakes  │  ├──── MistakeEntry (trade_id, mistake_id, description)
│     1:N    │──┘
│            │
│     1:N    │──┐
│   Tags     │  ├──── TradeTag (trade_id, tag_id)
│            │──┘
│            │
│     1:N    │── Attachment (trade_id, file_path, type, caption, order)
│            │
│     1:N    │── Note (trade_id, content, created_at)
│            │
│     1:N    │── TradeReview (trade_id, content, rating, lessons)
└────────────┘
```

### Detailed Relationship Table

| Entity A | Relationship | Entity B | Cardinality | Details |
|----------|-------------|----------|-------------|---------|
| Trade | belongs_to | Account | N:1 | **Required**. A trade MUST belong to exactly one account. |
| Trade | belongs_to | Asset | N:1 | **Required**. A trade MUST have an asset. |
| Trade | belongs_to | Broker | N:1 | Optional. Nullable FK. |
| Trade | belongs_to | MarketSession | N:1 | Optional. Nullable FK. |
| Trade | belongs_to | Timeframe | N:1 | Optional. Nullable FK. |
| Trade | belongs_to | Strategy | N:1 | Optional. Nullable FK. |
| Trade | belongs_to | Setup | N:1 | Optional. Nullable FK. |
| Trade | belongs_to | RiskProfile | N:1 | Optional. Nullable FK. |
| Trade | belongs_to | TradingSession | N:1 | Optional. Nullable FK. |
| Trade | has_many | EmotionEntry | 1:N | Cascade delete. |
| Trade | has_many | MistakeEntry | 1:N | Cascade delete. |
| Trade | has_many | Attachment | 1:N | Cascade delete. |
| Trade | has_many | Note | 1:N | Cascade delete. |
| Trade | has_many | TradeReview | 1:N | Cascade delete. |
| Trade | has_many | TradeTag | 1:N | Cascade delete. |
| Account | has_many | Trade | 1:N | Restrict delete (can't delete account with trades). |
| Asset | belongs_to | Market | N:1 | Required. Each asset is in exactly one market. |
| Asset | has_many | Trade | 1:N | Restrict delete (can't delete asset with trades). |
| Strategy | has_many | Trade | 1:N | Set-NULL on delete (trades keep strategy_id=NULL). |
| Strategy | has_many | Setup | M:N | Via `StrategySetup` junction table. |
| Strategy | has_one | RiskProfile | 1:1 | Optional. A strategy can have its own risk profile. |
| Setup | has_many | Trade | 1:N | Set-NULL on delete. |
| Setup | has_many | Strategy | M:N | Via `StrategySetup` junction table. |
| Emotion | has_many | EmotionEntry | 1:N | Restrict delete. |
| Tag | has_many | TradeTag | 1:N | Restrict delete. |
| Mistake | has_many | MistakeEntry | 1:N | Restrict delete. |
| RiskProfile | has_many | Trade | 1:N | Set-NULL on delete. |
| RiskProfile | belongs_to | Strategy | 1:1 | Optional. A risk profile can be standalone or linked to a strategy. |
| TradingSession | has_many | Trade | 1:N | Set-NULL on delete. |

---

## Stage 2.3 — Business Rules (Domain Invariants)

### Trade Invariants (Hard Rules)

| ID | Rule | Violation | Enforcement |
|----|------|-----------|-------------|
| BR-01 | A trade MUST have an asset (asset_id NOT NULL) | Incomplete trade creation | DB NOT NULL + service validation |
| BR-02 | A trade MUST have a direction ('long' or 'short') | Invalid trade | DB CHECK constraint + Pydantic validation |
| BR-03 | A trade MUST have quantity > 0 | Zero/negative size | DB CHECK + service validation |
| BR-04 | A trade MUST have entry_price > 0 | Zero/negative price | DB CHECK + service validation |
| BR-05 | A trade MUST have entry_datetime | No timestamp | DB NOT NULL |
| BR-06 | A trade MUST belong to exactly one account (account_id NOT NULL) | Orphan trade | DB NOT NULL + FK |
| BR-07 | Stop loss MUST be on the correct side (long: SL < entry, short: SL > entry) | Invalid SL | Service validation (too complex for DB CHECK alone) |
| BR-08 | Take profit MUST be on the correct side (long: TP > entry, short: TP < entry) | Invalid TP | Service validation |
| BR-09 | If both SL and TP are set, the risk zone (entry→SL) and reward zone (entry→TP) MUST be in opposite directions from entry | No valid risk-reward | Service validation |
| BR-10 | exit_price and exit_datetime are both NULL (open trade) OR both set (closed trade) | Inconsistent state | Service validation |
| BR-11 | status MUST be 'open' or 'closed' | Invalid status | DB CHECK + Pydantic |
| BR-12 | A trade CANNOT be modified after 30 days of being closed (immutable audit) | Late edit | Service — soft-lock via `editable_until` field |
| BR-13 | position_size (account currency) MUST be >= 0 if set | Negative position | DB CHECK |

### Entity Invariants

| ID | Rule | Enforcement |
|----|------|-------------|
| BR-14 | Strategy name MUST be unique per user (single-user → globally unique) | DB UNIQUE index |
| BR-15 | Setup name MUST be unique | DB UNIQUE index |
| BR-16 | Asset symbol + market_id MUST be unique (EUR/USD is unique in forex) | DB UNIQUE index (symbol, market_id) |
| BR-17 | Broker name SHOULD be unique (encouraged but not enforced at DB level) | Service suggestion |
| BR-18 | Emotion name MUST be unique | DB UNIQUE index |
| BR-19 | Tag name MUST be unique | DB UNIQUE index |
| BR-20 | Mistake name MUST be unique | DB UNIQUE index |
| BR-21 | A tag name MUST be non-empty and trimmed (no leading/trailing whitespace) | Service validation |
| BR-22 | EmotionEntry intensity MUST be between 1 and 10 inclusive | DB CHECK |
| BR-23 | EmotionEntry.context MUST be one of: 'before_entry', 'during_trade', 'after_exit' | DB CHECK + Pydantic |
| BR-24 | An Attachment file MUST NOT exceed 10 MB (file size limit enforced at upload) | Service validation |
| BR-25 | A trade's commission and swap_fees MUST default to 0 (non-negative) | DB DEFAULT + CHECK |
| BR-26 | Account name MUST be unique (single-user) | DB UNIQUE index |
| BR-27 | Account.status MUST be 'active' or 'inactive' | DB CHECK + Pydantic |
| BR-28 | TradingSession MUST have a name and a datetime range (start >= end) | Service validation |

### Immutability Rule

| ID | Rule | Enforcement |
|----|------|-------------|
| BR-29 | A Trade MUST NEVER be physically deleted from the database. It may only be archived (via status='archived') or marked inactive. All related data (emotions, attachments, reviews, notes, tags) MUST be preserved for traceability. | Service — `DELETE` is PROHIBITED at the API layer. Only `is_active` flag or `status='archived'` transitions allowed. DB-level: use INSTEAD OF triggers or soft-delete pattern. |

### Derived Value Rules

| ID | Rule | Details |
|----|------|---------|
| BR-25 | pnl MUST be recalculated whenever entry_price, exit_price, quantity, direction, commission, or swap_fees change | Service — computed column or trigger |
| BR-26 | r_multiple MUST be recalculated when exit_price changes | Only valid if SL was set on entry |
| BR-27 | Risk amount (risk_amount) is calculated as |entry_price - stop_loss| × quantity × pip_cost | Service on save |
| BR-28 | win/loss classification: pnl > 0 → win, pnl < 0 → loss, pnl = 0 → breakeven | Computed, not stored |

---

## Stage 2.4 — ER Model Approach Discussion

### Approach 1: Single Wide Trade Table (Recommended)

Store all core trade fields in a single `trades` table with FKs to lookup tables. Separate junction tables for M:N relationships.

```
trades
├── id (PK)
├── asset_id (FK, NOT NULL)
├── broker_id (FK, NULL)
├── strategy_id (FK, NULL)
├── setup_id (FK, NULL)
├── risk_profile_id (FK, NULL)
├── session_id (FK, NULL)
├── timeframe_id (FK, NULL)
├── direction (TEXT, NOT NULL, CHECK in {'long','short'})
├── status (TEXT, NOT NULL, CHECK in {'open','closed'})
├── entry_price (REAL, NOT NULL)
├── exit_price (REAL, NULL)
├── stop_loss (REAL, NULL)
├── take_profit (REAL, NULL)
├── quantity (REAL, NOT NULL)
├── position_size (REAL, NULL)
├── commission (REAL, DEFAULT 0)
├── swap_fees (REAL, DEFAULT 0)
├── risk_amount (REAL, NULL)
├── pnl (REAL, NULL)
├── pnl_points (REAL, NULL)
├── r_multiple (REAL, NULL)
├── entry_datetime (TEXT, NOT NULL)  -- ISO 8601
├── exit_datetime (TEXT, NULL)
├── editable_until (TEXT, NULL)       -- soft-lock timestamp
├── created_at (TEXT, NOT NULL)
├── updated_at (TEXT, NOT NULL)
└── notes_override (TEXT, NULL)       -- short inline note for quick journaling
```

**Pros**:
- Single-query reads for 95% of UI screens (journal list, metrics computation, dashboard)
- No joins needed for basic trade display
- Simple to index, simple to migrate
- SQLite handles wide tables efficiently (row-level storage)

**Cons**:
- Many nullable columns (standard for optional relationships)
- Schema changes more impactful than normalized extremes

### Approach 2: Hyper-Normalized (Trade Attributes as Rows)

Store trade data in an entity-attribute-value (EAV) pattern or separate `trade_details` table.

**Pros**: Extremely flexible, easy to add new fields.
**Cons**: Horrible read performance, nightmare queries, requires pivots. This is an anti-pattern for a journaling app where schema is well-defined. **REJECTED.**

### Approach 3: JSONB Trade Data (Single Table with JSON Column)

Store most trade data as a single JSON column with only PK and a few indexed fields as columns.

**Pros**: Flexible schema, easy to extend.
**Cons**: No FK enforcement inside JSON, no DB-level CHECK constraints, no indexing on individual fields, SQLite JSON support is less mature than PostgreSQL. **REJECTED.**

### Attachments: Separate Table (NOT BLOB) — replaces Screenshot

| Approach | Pros | Cons |
|----------|------|------|
| **BLOB in DB** | Single backup, transactional consistency | Bloats DB, slow reads, can't serve via static files, no CDN, backup sizes explode |
| **File paths in DB** (recommended) | DB stays small, files served via static file middleware, easy backup (DB + /data/attachments), CDN-friendly | Need to manage file lifecycle (cleanup on trade delete) |

**Recommendation**: Store file paths. Max file size 10 MB. Store in `data/attachments/{trade_id}/{uuid}.{ext}`. Reference via `attachments` table with a `type` field for categorization (image, pdf, document, video):

```
attachments
├── id (PK)
├── trade_id (FK, NOT NULL)
├── file_path (TEXT, NOT NULL)
├── type (TEXT, NOT NULL, CHECK in {'image','pdf','document','video','other'})
├── original_name (TEXT, NULL)        -- user-friendly filename
├── caption (TEXT, NULL)
├── file_size_bytes (INT, NULL)
├── mime_type (TEXT, NULL)
├── sort_order (INT, DEFAULT 0)
├── created_at (TEXT, NOT NULL)
```

### Tags: Junction Table (NOT JSON Array)

| Approach | Pros | Cons |
|----------|------|------|
| **JSON array in trade** | Simple model, no join for trade read | Can't enforce FK, no index on tag values, duplicates possible, no tag auto-complete based on existing values, can't query "all trades with tag X" efficiently |
| **Separate tags + trade_tags** (recommended) | FK integrity, unique tag names, efficient filtering, auto-complete, tag analytics | Extra join for read (trivial with SQLite FK index) |

### Emotions: Junction Table with Metadata

NOT a simple M:N. Use an entry table that records:
- which emotion (FK → emotions)
- intensity (1-10)
- timing context (before/during/after)
- timestamp

This enables rich psychology analytics (e.g., "do I feel fear most often before entry?").

### Performance Metrics: Computed, Not Stored

Analytics metrics (Sharpe, Sortino, win rate, drawdown, profit factor) are COMPUTED ON-THE-FLY from trades. This is the correct approach because:

1. **Metrics change whenever a trade is closed or modified** — stored metrics go stale immediately
2. **Different date ranges produce different metrics** — pre-computing doesn't help
3. **SQLite can aggregate thousands of trades in milliseconds** — a full scan of indexed trades by date is fast for a personal journal (tens of thousands of trades, not millions)
4. **No sync issues** — the source of truth is always the trades table

**Caveat**: For very large datasets (100k+ trades), a `metrics_cache` table with materialized aggregates by date range can be added later. This is premature optimization now.

---

## Stage 2.5 — Physical Design Approach

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Tables | lowercase, snake_case, plural | `trades`, `assets`, `trade_tags` |
| Columns | lowercase, snake_case | `entry_price`, `exit_datetime` |
| Primary keys | `id` (INTEGER PRIMARY KEY AUTOINCREMENT) | `id` |
| Foreign keys | `{referenced_table_singular}_id` | `asset_id`, `strategy_id` |
| Junction tables | `{table_a}_{table_b}` (sorted alphabetically) | `strategy_setups` (not `setups_strategies`) |
| Unique constraints | `uq_{table}_{columns}` | `uq_assets_symbol_market` |
| Indexes | `ix_{table}_{column}` | `ix_trades_entry_datetime` |
| CHECK constraints | `ck_{table}_{column}` | `ck_trades_direction` |

### Data Types

| Domain | SQLite Type | Python Type | Notes |
|--------|-------------|-------------|-------|
| Identifiers | `INTEGER` | `int` | PKs, FKs |
| Monetary amounts | `REAL` | `float` / `Decimal` | `entry_price`, `pnl`, `risk_amount` |
| Quantities | `REAL` | `float` | `quantity`, `position_size` |
| Exact decimals | `REAL` | `Decimal` (Pydantic handles conversion) | For display formatting |
| Booleans | `INTEGER` (0/1) | `bool` | SQLite has no native BOOLEAN |
| Text/strings | `TEXT` | `str` | Names, notes, descriptions |
| Timestamps | `TEXT` | `datetime` (ISO 8601) | SQLite has no native DATETIME — ISO 8601 text is lexicographically sortable |
| Enums | `TEXT` + `CHECK` | Python `enum.StrEnum` | `direction`, `status` |
| File sizes | `INTEGER` | `int` | Bytes |
| Sort orders | `INTEGER` | `int` | `sort_order`, `intensity` |

### Timestamp Strategy

Store all timestamps as ISO 8601 TEXT (`2026-07-06T15:30:00.000Z`). This is the recommended approach for SQLite because:
- Human-readable
- Lexicographically sortable (ORDER BY works)
- Timezone-aware (always UTC)
- SQLite's datetime functions work with this format

Why not Unix epoch integers? Not human-readable, timezone-agnostic, requires conversion for debugging.

### Enum Handling

SQLite has no ENUM type. Strategy:
1. Define Python `StrEnum` classes for fixed values (Direction, TradeStatus, EmotionContext)
2. Use TEXT columns with CHECK constraints at the DB level for data integrity
3. Pydantic validates at the API boundary
4. Both layers must agree — the Python enum `.value` matches the DB string

```python
class Direction(StrEnum):
    LONG = "long"
    SHORT = "short"

class TradeStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"

class EmotionContext(StrEnum):
    BEFORE_ENTRY = "before_entry"
    DURING_TRADE = "during_trade"
    AFTER_EXIT = "after_exit"
```

### Lookup Tables (Seed Data)

These small tables are pre-populated via Alembic seed data migrations:

**markets**: forex, crypto, stocks, futures, indices, commodities, bonds, options

**sessions**: pre_market, morning, afternoon, after_hours, asian_session, london_session, new_york_session

**timeframes**: M1, M5, M15, M30, H1, H2, H4, D1, W1, MN

**Default emotions**: fear, greed, confidence, anxiety, euphoria, frustration, calm, impatience, doubt, satisfaction, regret, boredom

**Default mistakes**: fomo_entry, revenge_trade, premature_entry, late_entry, missed_exit, cutting_winner_early, moving_sl, oversized_position, no_stop_loss, trading_without_plan, over_trading

### Index Strategy

```sql
-- Primary keys (auto-indexed by SQLite for INTEGER PRIMARY KEY)
-- Every table has `id INTEGER PRIMARY KEY AUTOINCREMENT`

-- Foreign key indexes (for JOIN performance)
CREATE INDEX ix_trades_account_id ON trades(account_id);
CREATE INDEX ix_trades_asset_id ON trades(asset_id);
CREATE INDEX ix_trades_strategy_id ON trades(strategy_id);
CREATE INDEX ix_trades_setup_id ON trades(setup_id);
CREATE INDEX ix_trades_broker_id ON trades(broker_id);
CREATE INDEX ix_trades_market_session_id ON trades(market_session_id);
CREATE INDEX ix_trades_timeframe_id ON trades(timeframe_id);
CREATE INDEX ix_trades_risk_profile_id ON trades(risk_profile_id);
CREATE INDEX ix_trades_trading_session_id ON trades(trading_session_id);

-- Date range queries (most common analytics pattern: "trades in date range")
CREATE INDEX ix_trades_entry_datetime ON trades(entry_datetime);
CREATE INDEX ix_trades_exit_datetime ON trades(exit_datetime);

-- Composite: filter by status + date range (dashboard "recent open/closed trades")
CREATE INDEX ix_trades_status_entry_datetime ON trades(status, entry_datetime);

-- Composite: performance by asset over time
CREATE INDEX ix_trades_asset_entry_datetime ON trades(asset_id, entry_datetime);

-- Composite: performance by strategy over time
CREATE INDEX ix_trades_strategy_entry_datetime ON trades(strategy_id, entry_datetime);

-- Composite: performance by setup over time
CREATE INDEX ix_trades_setup_entry_datetime ON trades(setup_id, entry_datetime);

-- Direction for filtering
CREATE INDEX ix_trades_direction ON trades(direction);

-- Unique indexes for entity integrity
CREATE UNIQUE INDEX uq_strategies_name ON strategies(name);
CREATE UNIQUE INDEX uq_setups_name ON setups(name);
CREATE UNIQUE INDEX uq_assets_symbol_market ON assets(symbol, market_id);
CREATE UNIQUE INDEX uq_emotions_name ON emotions(name);
CREATE UNIQUE INDEX uq_tags_name ON tags(name);
CREATE UNIQUE INDEX uq_mistakes_name ON mistakes(name);

-- Junction table indexes (composite PKs cover most queries, but inverse lookup needs index)
CREATE INDEX ix_trade_tags_tag_id ON trade_tags(tag_id);
CREATE INDEX ix_trade_emotions_emotion_id ON trade_emotions(emotion_id);
CREATE INDEX ix_trade_mistakes_mistake_id ON trade_mistakes(mistake_id);
CREATE INDEX ix_screenshots_trade_id ON screenshots(trade_id);
CREATE INDEX ix_notes_trade_id ON notes(trade_id);

-- Junction table composite PKs:
-- trade_tags: PRIMARY KEY (trade_id, tag_id)  -- auto-indexed
-- trade_emotions: PRIMARY KEY (trade_id, emotion_id, context, timestamp) -- auto-indexed
-- trade_mistakes: PRIMARY KEY (trade_id, mistake_id) -- auto-indexed
-- strategy_setups: PRIMARY KEY (strategy_id, setup_id) -- auto-indexed
```

### Foreign Key & Cascade Rules

```sql
PRAGMA foreign_keys = ON;  -- At connection level

-- trades → assets          : RESTRICT (can't delete asset with trades)
-- trades → brokers         : SET NULL
-- trades → strategies      : SET NULL
-- trades → setups          : SET NULL
-- trades → sessions        : SET NULL
-- trades → timeframes      : SET NULL
-- trades → risk_profiles   : SET NULL
-- trade_tags → trades      : CASCADE
-- trade_tags → tags        : RESTRICT
-- trade_emotions → trades  : CASCADE
-- trade_emotions → emotions: RESTRICT
-- trade_mistakes → trades  : CASCADE
-- trade_mistakes → mistakes: RESTRICT
-- screenshots → trades     : CASCADE (delete screenshots when trade is deleted)
-- notes → trades           : CASCADE
-- strategy_setups → strategies: CASCADE
-- strategy_setups → setups  : CASCADE
```

### Migration Strategy

1. Enable Alembic auto-generation (`alembic revision --autogenerate`)
2. Wire `target_metadata = Base.metadata` in `alembic/env.py`
3. Create Base in `app/database.py`: `Base = declarative_base()` (or use SQLAlchemy 2.0 `DeclarativeBase`)
4. Single initial migration creating ALL tables
5. Seed data migration for lookup tables (markets, sessions, timeframes, default emotions, default mistakes)
6. Subsequent changes follow normal Alembic flow

### File Layout for Models

```
backend/app/
├── database.py          ← Add `Base = declarative_base()` + enable foreign keys
├── models/
│   ├── __init__.py      ← Re-export all models (from .trade import Trade, etc.)
│   ├── trade.py         ← Trade model
│   ├── asset.py         ← Asset, Market models
│   ├── broker.py        ← Broker model
│   ├── session.py       ← Session model
│   ├── timeframe.py     ← Timeframe model
│   ├── strategy.py      ← Strategy, StrategySetup models
│   ├── setup.py         ← Setup model
│   ├── emotion.py       ← Emotion, EmotionEntry models
│   ├── tag.py           ← Tag, TradeTag models
│   ├── mistake.py       ← Mistake, MistakeEntry models
│   ├── screenshot.py    ← Screenshot model
│   ├── note.py          ← Note model
│   └── risk_profile.py  ← RiskProfile model
```

---

## Key Questions — Answered

### Q1: What is the canonical entity list? Are there entities I'm missing?

**15 entities** (listed in Stage 2.1 above). Deliberately excluded: `User` (single-user app), `BacktestResult` (future phase), `TradingPlan` (same as Strategy in this domain), `PriceData` (future data pipeline).

### Q2: What are the most important relationships?

Trade → Asset (N:1, mandatory) is the most critical. Trade → Strategy (N:1) and Trade → Setup (N:1) are the analytical backbone. Trade → EmotionEntry (1:N) enables psychology analysis. All junction tables (tags, emotions, mistakes) feed the multi-dimensional analytics.

### Q3: What validation/immutable rules protect data integrity?

See BR-01 through BR-28 in Stage 2.3. The most critical: every trade needs an asset, direction, entry price, quantity, and entry datetime. SL/TP direction validation prevents impossible risk setups. The 30-day soft-lock prevents retrospective journal manipulation.

### Q4: Should analytics be stored or computed on-the-fly?

**Computed on-the-fly.** Personal trading journals have at most tens of thousands of trades — SQLite aggregates this in milliseconds. Stored metrics are always stale and create cache-invalidation nightmares. A `metrics_cache` materialized-view table can be added post-MVP if performance becomes an issue.

### Q5: How do we model psychology — per trade or per session?

**Per trade**, via the `EmotionEntry` junction table. Each trade can have multiple emotion records at different points (before entry, during, after exit). Trading sessions are about time-of-day context, not psychology. The session entity is distinct.

### Q6: How do attachments relate to trades?

**1:N.** A single trade can have multiple attachments of different types: entry signal screenshots, trade management images, annotated PDF analysis, reference videos. The `attachments` table replaces the narrower `screenshots` concept and adds a `type` discriminator for extensibility. Screenhots are stored as attachments with `type='image'`.

### Q7: What's the difference between a Setup and a Strategy?

A **Strategy** is the overall trading plan (e.g., "Trend Following on Daily EUR/USD"): it defines market focus, risk rules, and high-level methodology. A **Setup** is a specific entry/exit pattern (e.g., "Bull Flag on 1H", "Engulfing Candle", "RSI Divergence"). A strategy can use multiple setups. A setup can belong to multiple strategies (M:N via `strategy_setups`). In practice, most trades will link to ONE setup and ONE strategy.

### Q8: Should tags be free-form or from a predefined list?

**Free-form**, backed by a `tags` table with a UNIQUE constraint on name. The UI provides auto-complete from existing tags during entry. This gives maximum flexibility (any tag the user wants) while enforcing consistency (misspelled tags won't create duplicates). The junction table enables efficient filtering and tag-based analytics.

---

## Approaches Comparison

### Trade Table Design

| Approach | Pros | Cons | Effort |
|----------|------|------|--------|
| **Single wide table** (recommended) | Fast reads, simple queries, easy indexing, good for journal UI + analytics | Many nullable columns | Low |
| Hyper-normalized (EAV) | Maximum flexibility | Horrible query performance, complex pivots | High |
| JSON column for trade data | Flexible schema | No FK/CHECK enforcement, poor indexing, hard to migrate | Medium |

### Attachment Storage (replaces Screenshot)

| Approach | Pros | Cons |
|----------|------|------|
| **File paths in DB** (recommended) | Small DB, fast reads, CDN-servable, easy backup strategy, type-discriminated | File lifecycle management needed |
| BLOB in DB | Single backup, transactional | Bloats DB, slow, no static serving |
| Cloud storage URLs | Offloads storage | Offline-first requirement → need local fallback |

### Tag Model

| Approach | Pros | Cons |
|----------|------|------|
| **Junction table** (recommended) | FK integrity, efficient filtering, auto-complete, analytics | Extra join (trivial cost) |
| JSON array in trade | No join, simple reads | No integrity, no efficient tag filtering, duplicates risk, no tag reuse analytics |

### Metrics Strategy

| Approach | Pros | Cons |
|----------|------|------|
| **Compute on-the-fly** (recommended) | Always correct, no sync issues, simple implementation | Slightly higher latency for large datasets |
| Stored/cached metrics | Fast dashboard loads | Stale data, invalidation complexity, wrong answers are dangerous |
| Materialized cache table | Best of both | Premature optimization for MVP — revisit at 100k+ trades |

## Recommendation

**Adopt the single wide trade table** approach with proper normalization for supporting entities. The design follows these principles:

1. **Trade as the central aggregate** — one table with all core fields, FKs to lookup tables, no JSON blobs
2. **Account ownership** — every trade belongs to an account, enabling multi-account trading
3. **Junction tables for M:N** — tags, emotions, mistakes all use proper junction/entry tables with metadata
4. **File paths for attachments** — DB stores paths, files live on filesystem under `data/attachments/`, type-discriminated
5. **TradeReview separate from Note** — quick inline notes vs structured post-trade reviews
6. **Distinct sessions** — MarketSession (market hours) vs TradingSession (user work session grouping trades)
7. **Lookup tables for enums** — small tables pre-seeded via migration for markets, sessions, timeframes, emotions, mistakes
8. **Computed metrics** — analytics always reads from source trades; no stored metric tables. RiskProfile contains only configuration, never calculated values.
9. **Soft-delete / Archive** — trades are NEVER physically deleted. `is_active` flag or `archived` status preserves traceability (BR-29).
10. **Soft-lock for audit** — trades become read-only 30 days after closing

This approach gives clean data, fast reads, referential integrity, and analytical power without over-engineering. It aligns with the offline-first SQLite architecture and keeps the schema simple enough for future migration to PostgreSQL if needed.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Schema changes to Trade table become expensive as data grows | Medium | High | Get it right in design phase. Use additive migrations (new columns are cheap in SQLite). |
| REAL precision for monetary amounts could cause rounding errors | Low | Medium | Pydantic handles Decimal → float conversion. Display formatting rounds to pip/cent precision. SQLite REAL is IEEE 64-bit — sufficient for 15 significant digits. |
| Foreign key pragma not enabled at connection level → silent data corruption | Medium | Critical | Enable in `database.py` `init_db()`, verify with `PRAGMA foreign_keys` on startup. Add test asserting it's ON. |
| Screenshot file cleanup on trade delete could leak files | Medium | Low | Service-layer cascade cleanup before archiving trade. Periodic cleanup job as post-MVP. |
| Seed data migrations conflict with user-created entities | Low | Medium | Seed IDs use negative or high ranges. Better: seed by name, not ID. |
| Computed metrics become slow at scale | Low (MVP) | Medium | Add `metrics_cache` materialized table when profiling proves it's needed. Not before. |
| Checklist: `PRAGMA foreign_keys` must be set PER CONNECTION, not just in init | High | Critical | Add SQLAlchemy `@event.listens_for(engine, "connect")` to set it every time. Verify with test. |

## Ready for Proposal

**Yes.** This exploration covers all entities, relationships, business rules, ER approach, and physical design decisions needed to create a proposal. The orchestrator should proceed to `sdd-propose` with the following context:

- 19 entities identified with clear responsibilities (added Account, TradeReview, Attachment, TradingSession)
- 29 business rules defining domain invariants (added BR-06 account requirement, BR-26 Account name unique, BR-27 Account status, BR-28 TradingSession validation, BR-29 soft-delete)
- Single wide trade table design selected
- Junction table pattern for all M:N relationships
- File-path storage for attachments (replaces narrower Screenshot)
- On-the-fly metric computation (RiskProfile stores config only, never metrics)
- Soft-delete/archive for all trades — never physically deleted
- Comprehensive indexing strategy (14 individual indexes + 5 composite)
- Clear migration strategy via Alembic autogenerate

The domain model is ready for formal specification.
