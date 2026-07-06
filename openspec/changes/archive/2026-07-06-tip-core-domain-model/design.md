# Design: TIP Core Domain Model — Entities, Relationships, and Physical Schema

**Design for**: `tip-core-domain-model` change. Defines the canonical domain model (19 entities, 29 BRs, 21 tables) that every future TIP feature builds on. **Trade is the SSOT — no module creates an alternative trade representation.**

---

## 1. Conceptual Domain Model

Seven clusters of responsibility. Every entity belongs to exactly one owning module.

| Cluster | Entities | Owning Module | Responsibility |
|---------|----------|---------------|----------------|
| **Core Trading** | Trade, Account, Asset, Market, Broker, MarketSession, Timeframe | `trading_journal` | Trade execution, ownership, instrument classification |
| **Sessions** | TradingSession | `trading_journal` | User-defined work sessions grouping trades |
| **Strategy** | Strategy, Setup | `strategies`, `setups` | Trading plans and entry/exit patterns (M:N via `strategy_setups`) |
| **Psychology** | Emotion, EmotionEntry | `psychology` | Emotional state per trade phase with intensity (1–10) |
| **Risk** | RiskProfile | `risk_management` | Config-only presets with zero stored computed metrics |
| **Review** | Note, TradeReview, Attachment | `trading_journal`, `screenshot_library` | Inline notes, structured reviews, type-discriminated file references |
| **Cross-cutting** | Tag, Mistake, MistakeEntry | `trading_journal`, `error_management` | Free-form tagging, error classification with per-trade entries |

**Semantic spine**: Account → Trade (mandatory). Asset → Trade (mandatory). Trade aggregates EmotionEntry, MistakeEntry, Note, TradeReview, Attachment via CASCADE. Tag/Emotion/Mistake are immutable seeded catalogs referenced by junction/entry tables. Strategy/Setup/RiskProfile/TradingSession are optional lookups with SET NULL on delete. **Derived metrics (PnL, Sharpe, R:R) are computed on-the-fly — never stored.**

---

## 2. Logical ER Diagram

```
                    ||-----------o{
                    |  Account    |── trades
                    |-------------|
                    | name UQ     |
                    ||-----------o{

   ||-------||       ||-----------o{         ||-------||
   | Market |───o{   |   Trade    |──o{      | Broker |
   |--------|   |    | (CANONICAL)|   |      |--------|
   ||-------||   |    |-----------|   |      ||-------||
                 |    |direction  |   |
   ||-------||   |    |entry_price|   |      ||---------||
   |  Asset  |───||   |quantity   |   o{----|  Emotion  |
   |---------|       |status     |   |       |----------|
   |sym+mkt UQ       |account_id |   |       ||---------||
   ||-------||       ||----||----||   |
                      |    |    |     o{----|  Mistake  |
                      |    |    |               |---------|
    optional FK:      |    |    |               ||-------||
    broker_id,        |    |    |
    market_session_id |    |    |     o{----||---------||
    timeframe_id,     |    |    |          |   Tag    |
    strategy_id,      |    |    |          |---------||
    setup_id,         |    |    |          ||---------||
    risk_profile_id,  |    |    |
    trading_session_id|    |    o{----------||--------------||
                      |    |               |  EmotionEntry  |
                      |    o{----------||  |  (intensity,   |
                      |               |   |   context)      |
                      |               |   ||--------------||
                      |    o{----------||
                      |               |  |  MistakeEntry  |
                      |               |   ||--------------||
                      |    o{----------||
                      |               |  | TradeTag (Jxn) |
                      |               |   ||--------------||
                      |    o{--------||---------||
                      |             |  Note    |
                      |             ||---------||
                      |    o{--------||--------------||
                      |             | TradeReview   |
                      |             ||--------------||
                      |    o{--------||-------------||
                      |             | Attachment    |
                      |             | (type disc.)  |
                      |             ||-------------||

   Strategy ||----o{|| strategy_setups ||----o{|| Setup
            |      |  (M:N junction)   |       |
            ||----||                   ||-----||

   RiskProfile ──o| Strategy
   (optional 1:1, SET NULL)
```

**Cardinality legend**: `||` = mandatory 1, `o|` = optional 1, `||--o{` = 1 to many (mandatory side), `|--o{` = 1 to many (optional side), `o{--o{` = M:N.

---

## 3. Relational Model

| Relation | Type | Attributes | PK | FKs |
|----------|------|------------|----|-----|
| `accounts` | Entity | id, name (UQ), broker, account_type, base_currency, status, is_active, created_at, updated_at | id | — |
| `assets` | Entity | id, market_id, symbol, name, is_active, created_at, updated_at | id | market_id → markets |
| `markets` | Catalog | id, name, created_at | id | — |
| `brokers` | Catalog | id, name, is_active, created_at, updated_at | id | — |
| `market_sessions` | Catalog | id, name, created_at | id | — |
| `timeframes` | Catalog | id, name, created_at | id | — |
| `trades` | Core | id, account_id, asset_id, broker_id, market_session_id, timeframe_id, strategy_id, setup_id, risk_profile_id, trading_session_id, direction, status, entry_price, exit_price, stop_loss, take_profit, quantity, position_size, commission, swap_fees, risk_amount, pnl, pnl_points, r_multiple, entry_datetime, exit_datetime, editable_until, notes_override, is_active, created_at, updated_at | id | acct, asset, broker, mkt_session, tf, strategy, setup, rp, trading_session |
| `trading_sessions` | Entity | id, name, start_datetime, end_datetime, notes, is_active, created_at, updated_at | id | — |
| `strategies` | Entity | id, name (UQ), description, is_active, created_at, updated_at | id | — |
| `setups` | Entity | id, name (UQ), description, is_active, created_at, updated_at | id | — |
| `strategy_setups` | Junction | strategy_id, setup_id | (strategy_id, setup_id) | strategy_id → strategies (CASCADE), setup_id → setups (CASCADE) |
| `risk_profiles` | Entity | id, name, strategy_id, max_risk_per_trade, position_sizing_method, max_daily_loss, max_concurrent_trades, is_active, created_at, updated_at | id | strategy_id → strategies (SET NULL) |
| `emotions` | Catalog | id, name (UQ), created_at | id | — |
| `emotion_entries` | Entry | id, trade_id, emotion_id, intensity, context, notes, created_at | id | trade_id → trades (CASCADE), emotion_id → emotions (RESTRICT) |
| `tags` | Catalog | id, name (UQ), created_at | id | — |
| `trade_tags` | Junction | trade_id, tag_id | (trade_id, tag_id) | trade_id → trades (CASCADE), tag_id → tags (RESTRICT) |
| `mistakes` | Catalog | id, name (UQ), created_at | id | — |
| `mistake_entries` | Entry | id, trade_id, mistake_id, notes, created_at | id | trade_id → trades (CASCADE), mistake_id → mistakes (RESTRICT) |
| `notes` | Entity | id, trade_id, content, created_at, updated_at | id | trade_id → trades (CASCADE) |
| `trade_reviews` | Entity | id, trade_id, content, rating_grade, lesson_learned, created_at, updated_at | id | trade_id → trades (CASCADE) |
| `attachments` | Entity | id, trade_id, file_path, type, original_name, caption, file_size_bytes, mime_type, sort_order, is_active, created_at | id | trade_id → trades (CASCADE) |

---

## 4. Physical SQLite Schema

**Every table** has `id INTEGER PRIMARY KEY AUTOINCREMENT`. **Every table** with mutable data has `created_at TEXT NOT NULL` (ISO 8601 UTC). Timestamps use ISO 8601 UTC text (`2026-07-06T15:30:00.000Z`) — lexicographically sortable, human-readable, timezone-safe.

| Table | Key Columns & Types | CHECK Constraints | DEFAULT Values |
|-------|--------------------|--------------------|----------------|
| `accounts` | name TEXT NOT NULL, status TEXT NOT NULL, base_currency TEXT | `ck_accounts_status`: status IN ('active', 'inactive') | status = 'active', base_currency = 'USD' |
| `assets` | symbol TEXT NOT NULL, market_id INTEGER NOT NULL | `uq_assets_symbol_market`: UNIQUE(symbol, market_id) | — |
| `markets` | name TEXT NOT NULL | — | — |
| `brokers` | name TEXT NOT NULL | — | — |
| `market_sessions` | name TEXT NOT NULL | — | — |
| `timeframes` | name TEXT NOT NULL | — | — |
| `trades` | account_id INTEGER NOT NULL, asset_id INTEGER NOT NULL, direction TEXT NOT NULL, entry_price REAL NOT NULL, quantity REAL NOT NULL, entry_datetime TEXT NOT NULL, status TEXT NOT NULL, position_size REAL NULL | `ck_trades_direction`: direction IN ('long','short'); `ck_trades_status`: status IN ('open','closed'); `ck_trades_entry_price`: entry_price > 0; `ck_trades_quantity`: quantity > 0; `ck_trades_position_size`: position_size >= 0; `ck_trades_commission`: commission >= 0; `ck_trades_swap`: swap_fees >= 0 | commission = 0, swap_fees = 0, is_active = 1 |
| `trading_sessions` | name TEXT NOT NULL, start_datetime TEXT NOT NULL, end_datetime TEXT NULL | — | — |
| `strategies` | name TEXT NOT NULL, description TEXT NULL | `uq_strategies_name`: UNIQUE(name) | is_active = 1 |
| `setups` | name TEXT NOT NULL, description TEXT NULL | `uq_setups_name`: UNIQUE(name) | is_active = 1 |
| `strategy_setups` | strategy_id INTEGER NOT NULL, setup_id INTEGER NOT NULL | PK(strategy_id, setup_id) | — |
| `risk_profiles` | name TEXT NOT NULL, strategy_id INTEGER NULL | — | is_active = 1 |
| `emotions` | name TEXT NOT NULL | `uq_emotions_name`: UNIQUE(name) | — |
| `emotion_entries` | trade_id INTEGER NOT NULL, emotion_id INTEGER NOT NULL, intensity INTEGER NOT NULL, context TEXT NOT NULL | `ck_emotion_entries_intensity`: intensity BETWEEN 1 AND 10; `ck_emotion_entries_context`: context IN ('before_entry', 'during_trade', 'after_exit') | — |
| `tags` | name TEXT NOT NULL | `uq_tags_name`: UNIQUE(name) | — |
| `trade_tags` | trade_id INTEGER NOT NULL, tag_id INTEGER NOT NULL | PK(trade_id, tag_id) | — |
| `mistakes` | name TEXT NOT NULL | `uq_mistakes_name`: UNIQUE(name) | — |
| `mistake_entries` | trade_id INTEGER NOT NULL, mistake_id INTEGER NOT NULL, notes TEXT NULL | — | — |
| `notes` | trade_id INTEGER NOT NULL, content TEXT NOT NULL | — | — |
| `trade_reviews` | trade_id INTEGER NOT NULL, content TEXT NULL, rating_grade TEXT NULL, lesson_learned TEXT NULL | — | — |
| `attachments` | trade_id INTEGER NOT NULL, file_path TEXT NOT NULL, type TEXT NOT NULL, file_size_bytes INTEGER NULL, sort_order INTEGER | `ck_attachments_type`: type IN ('image', 'pdf', 'document', 'video', 'other') | sort_order = 0, is_active = 1 |

**Booleans**: stored as `INTEGER` (0/1). **Monetary**: `REAL` (IEEE 64-bit float). **Enums**: TEXT + CHECK with Python `StrEnum.value` matching exactly.

---

## 5. Index Strategy

| Pattern | Count | Naming | Target |
|---------|-------|--------|--------|
| FK indexes | 14 | `ix_{table}_{fk}` | `ix_trades_account_id`, `ix_trades_asset_id`, `ix_trades_broker_id`, `ix_trades_market_session_id`, `ix_trades_timeframe_id`, `ix_trades_strategy_id`, `ix_trades_setup_id`, `ix_trades_risk_profile_id`, `ix_trades_trading_session_id`, `ix_emotion_entries_emotion_id`, `ix_trade_tags_tag_id`, `ix_mistake_entries_mistake_id`, `ix_strategy_setups_setup_id`, `ix_strategy_setups_strategy_id` |
| Date range | 2 | `ix_{table}_{col}` | `ix_trades_entry_datetime`, `ix_trades_exit_datetime` |
| Composite | 3 | `ix_{tbl}_{c1}_{c2}` | `ix_trades_status_entry_datetime` (dashboard filter), `ix_trades_asset_entry_datetime` (perf by asset), `ix_trades_strategy_entry_datetime` (perf by strategy) |
| Direction | 1 | `ix_{tbl}_{col}` | `ix_trades_direction` |
| Junction inverse | 1 | `ix_{tbl}_{fk}` | `ix_strategy_setups_setup_id` (for setup → strategy lookup) |
| Unique integrity | 7 | `uq_{tbl}_{cols}` | `uq_strategies_name`, `uq_setups_name`, `uq_assets_symbol_market`, `uq_emotions_name`, `uq_tags_name`, `uq_mistakes_name`, `uq_accounts_name` |

**Total**: 14 FK + 2 date + 3 composite + 1 direction + 1 junction inverse + 7 unique = **28 indexes**. PKs are auto-indexed by SQLite's INTEGER PRIMARY KEY.

---

## 6. Referential Integrity Strategy

`PRAGMA foreign_keys = ON` per connection via `@event.listens_for(engine, "connect")` on the sync engine, with equivalent listener on the async engine. Every FK has explicit ON DELETE — no defaults.

| Parent | Child | ON DELETE | Rationale |
|--------|-------|-----------|-----------|
| accounts | trades | RESTRICT | Never orphan trades. Account must be deactivated, not deleted, while trades exist. |
| assets | trades | RESTRICT | Never orphan trades. Asset must be deactivated, not deleted. |
| markets | assets | RESTRICT | Seeded catalog — never deleted while assets reference it. |
| brokers | trades | SET NULL | Broker decommissioned — trades retain their data, broker link drops. |
| market_sessions | trades | SET NULL | Seeded catalog — session removed, trades keep other context. |
| timeframes | trades | SET NULL | Seeded catalog — timeframe removed, trades keep other context. |
| strategies | trades | SET NULL | Strategy deleted — trades retain all other data, strategy reference drops. |
| setups | trades | SET NULL | Setup deleted — trades keep other context. |
| risk_profiles | trades | SET NULL | Profile deleted — trades keep other context. |
| trading_sessions | trades | SET NULL | Session deleted — trades remain independent. |
| trades | emotion_entries | CASCADE | Trade archived → all emotion records cascade. |
| trades | mistake_entries | CASCADE | Trade archived → all mistake records cascade. |
| trades | trade_tags | CASCADE | Trade archived → all tag links cascade. |
| trades | notes | CASCADE | Trade archived → all notes cascade. |
| trades | trade_reviews | CASCADE | Trade archived → all reviews cascade. |
| trades | attachments | CASCADE | Trade archived → all attachment metadata cascade. |
| emotions | emotion_entries | RESTRICT | Seeded catalog — never deleted while entries reference it. |
| tags | trade_tags | RESTRICT | Never delete a tag still linked to trades. |
| mistakes | mistake_entries | RESTRICT | Seeded catalog — never deleted while entries reference it. |
| strategies | strategy_setups | CASCADE | Strategy deleted → junction rows cascade. |
| setups | strategy_setups | CASCADE | Setup deleted → junction rows cascade. |
| strategies | risk_profiles | SET NULL | Strategy deleted → profile becomes standalone. |

**BR-29 enforcement**: Service layer prohibits DELETE. The FK cascade only activates if a DELETE reaches the DB (e.g., via a future admin tool). Normal operation uses `is_active = 0` and/or `status = 'archived'`.

---

## 7. Migration Strategy

| Aspect | Decision |
|--------|----------|
| **Tool** | Alembic with `target_metadata = Base.metadata` in `alembic/env.py` |
| **Auto-generation** | `alembic revision --autogenerate -m "description"` after model definition |
| **Initial migration** | Single revision creating all 21 tables. Generated after all models are defined. |
| **Seed data** | Separate revision per lookup domain. Seeds by **stable name**, not ID (`op.get_bind().execute(tables["markets"].insert(), [{"name": "forex"}, ...])`). |
| **Seeded tables** | `markets` (7 rows), `market_sessions` (7 rows), `timeframes` (10 rows), `emotions` (12 rows), `mistakes` (11 rows) |
| **Naming** | Revision IDs: `{prefix}_{description}`. Seed revisions: `{prefix}_seed_{table}`. No custom naming convention — Alembic defaults. |
| **Down revisions** | Each seed revision includes a downgrade that deletes only seeded rows. |
| **Future changes** | Additive only (new columns, new tables). No destructive ALTER in MVP. New columns on Trade are nullable or have defaults. |
| **FK pragma note** | Alembic runs with `PRAGMA foreign_keys=OFF` (SQLite default). This allows defining FKs to tables that don't exist yet (required because SQLite lacks `ALTER TABLE ADD CONSTRAINT`). **This is SQLite-specific.** If the backend changes to PostgreSQL/MySQL, the migration sequence must be revised — those engines enforce FK references eagerly at DDL time. |

**`Base` location**: `app/models/__init__.py` re-exports all models. `app/database.py` defines `Base = declarative_base()`. `alembic/env.py` imports `from app.database import Base` and sets `target_metadata = Base.metadata`.

---

## 8. Risks and Design Decisions

### Key Decisions

| Option | Chosen | Rejected | Rationale |
|--------|--------|----------|-----------|
| Trade table shape | Single wide table with FKs | EAV / JSON column | Fast reads for 95% of queries; SQLite handles wide tables efficiently at journal scale |
| Attachment storage | File paths in DB | BLOB / cloud URLs | DB stays small; files served by middleware; offline-first compatible |
| Tag model | Separate `tags` + `trade_tags` junction | JSON array in trade | FK integrity, efficient filtering, auto-complete, tag analytics |
| Metrics storage | Compute on-the-fly | Stored/cached | Always correct; SQLite aggregates 10k trades in ms; no staleness risk |
| Risk storage | Config-only profile | Stored computed metrics | RiskProfile stores presets only — PnL, R:R, position sizing computed dynamically per request |
| Soft-delete | `is_active` flag + `status='archived'` | Physical DELETE | BR-29 — full traceability. Service layer prohibits DELETE API. |
| Audit soft-lock | `editable_until` 30d post-close | Hard-frozen at DB level | Service enforces; allows admin override if needed |

### Risks

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| FK pragma not set per async connection | Medium | `@event.listens_for(engine.sync_engine, "connect")` — verify with test |
| REAL precision for monetary amounts | Low | IEEE 64-bit sufficient for 15 sig figs; Pydantic handles Decimal→float |
| Trade schema changes at scale | Medium | Additive migrations only; get it right in design; SQLite ALTER TABLE ADD COLUMN is O(1) |
| Seed data ID drift | Low | Seed by name, not ID; `INSERT OR IGNORE` with name matching |
| Soft-lock bypassed by direct DB write | Low | Acceptable — single-user offline app; service layer is the contract |

---

## 9. Domain Evolution Policy

Three permanent policies governing how the TIP domain model evolves across versions.

### 9.1 Forward-Compatible Evolution

| Rule | Enforcement |
|------|-------------|
| Never repurpose the meaning of an existing entity | Each entity has a frozen semantic contract. A `Trade` is always a trade. |
| Never change the meaning of an existing field | `entry_price` is always the price at entry. No field redefinition. |
| New requirements → add entities, relations, or attributes | Do not modify existing semantics. Additive only. |
| Migrations SHALL be additive | `ALTER TABLE ADD COLUMN` (nullable or with default). No destructive ALTER outside a dedicated SDD. |
| Destructive changes require a new SDD initiative | Schema-wide refactors, column removals, or table drops MUST go through the full proposal→spec→design→tasks pipeline. |

### 9.2 Versioning

The domain model MUST evolve between versions maintaining backward data compatibility whenever reasonably possible. Existing data in `trades`, catalog entries, and user-created entities (strategies, tags, sessions) MUST remain readable and semantically valid after a version upgrade. Breaking changes require a data migration plan within the SDD that added them.

### 9.3 Canonical Dictionaries

Catalog entities (Market, MarketSession, Timeframe, Emotion, Mistake, Tag) are the **official dictionaries** of the domain. No free-text fields SHALL duplicate these concepts where an official entity exists. For example: trade direction uses the `direction` column with a CHECK constraint, not a free-text `notes` field. Emotion data uses `emotion_id` FK + `emotion_entries` table, not a `mood_notes` free-text column.

---

## 10. Traceability Matrix

### Proposal → Design Coverage

| Source | Target | Status |
|--------|--------|--------|
| `proposal.md` — 19 entities, 29 BRs | Sections 1–3 — all entities and BRs defined | ✓ |
| `proposal.md` — Single wide trade table | Section 1 — `trades` with 9 FKs, 33 columns | ✓ |
| `proposal.md` — FK cascade policies | Section 6 — 22 FK relationships with explicit ON DELETE | ✓ |
| `proposal.md` — 14 FK + 5 composite + 7 unique indexes | Section 5 — 28 indexes total (14 FK + 2 date + 3 composite + 1 direction + 1 inverse + 7 unique) | ✓ |
| `proposal.md` — Alembic + seed data strategy | Section 7 — migration strategy | ✓ |

### Spec → Design Coverage

| Spec Requirement | Design Section | Status |
|------------------|---------------|--------|
| Core domain — Entity Definition (19 entities) | §1 Conceptual Model (entity table), §3 Relational Model | ✓ |
| Core domain — Entity Relationships (C3) | §6 Referential Integrity (all 22 FKs) | ✓ |
| Core domain — BR-01 to BR-29 | §4 Physical Schema (CHECK/NOT NULL), §6 (cascades) | ✓ |
| Core domain — Extensibility (C5) | §7 additive-only migration pattern | ✓ |
| DB physical — Naming conventions | §3 table names, §4 column types, §5 index naming | ✓ |
| DB physical — C2 surrogate keys | §4 every table has `id INTEGER PRIMARY KEY AUTOINCREMENT` | ✓ |
| DB physical — Data types | §4 type map (TEXT for timestamps, REAL for money, INTEGER for bool) | ✓ |
| DB physical — CHECK constraints | §4 all CHECK constraints per table | ✓ |
| DB physical — Index strategy (14+5+7) | §5 exact count and naming | ✓ |
| DB physical — FK pragma (C3) | §6 `PRAGMA foreign_keys = ON` per connection | ✓ |
| DB physical — Migration strategy | §7 Alembic autogenerate, seed by name | ✓ |
| DB physical — C6 domain governs DB | §8 decision table, §1 conceptual spine | ✓ |

### Business Rule → Enforcement Mapping

| BR# | Rule | Enforcement Mechanism | Entity / Constraint |
|-----|------|----------------------|--------------------|
| BR-01 | asset_id NOT NULL | `trades.asset_id` NOT NULL + FK RESTRICT | Trade |
| BR-02 | direction in ('long','short') | CHECK `ck_trades_direction` | Trade |
| BR-03 | quantity > 0 | CHECK `ck_trades_quantity` | Trade |
| BR-04 | entry_price > 0 | CHECK `ck_trades_entry_price` | Trade |
| BR-05 | entry_datetime NOT NULL | `trades.entry_datetime` NOT NULL | Trade |
| BR-06 | account_id NOT NULL | `trades.account_id` NOT NULL + FK RESTRICT | Account → Trade |
| BR-07 | SL correct side | Service validation (SL < entry for long) | Trade |
| BR-08 | TP correct side | Service validation (TP > entry for long) | Trade |
| BR-09 | SL/TP opposite directions | Service validation | Trade |
| BR-10 | exit consistency (both NULL or both set) | Service validation | Trade |
| BR-11 | status in ('open','closed') | CHECK `ck_trades_status` | Trade |
| BR-12 | 30-day soft-lock | Service validates `editable_until` | Trade |
| BR-13 | position_size >= 0 | CHECK `ck_trades_position_size` | Trade |
| BR-14 | Strategy name UNIQUE | UNIQUE INDEX `uq_strategies_name` | strategies |
| BR-15 | Setup name UNIQUE | UNIQUE INDEX `uq_setups_name` | setups |
| BR-16 | Asset(symbol,market_id) UNIQUE | UNIQUE INDEX `uq_assets_symbol_market` | assets |
| BR-17 | Broker name SHOULD UNIQUE | Service suggestion (no DB constraint) | brokers |
| BR-18 | Emotion name UNIQUE | UNIQUE INDEX `uq_emotions_name` | emotions |
| BR-19 | Tag name UNIQUE | UNIQUE INDEX `uq_tags_name` | tags |
| BR-20 | Mistake name UNIQUE | UNIQUE INDEX `uq_mistakes_name` | mistakes |
| BR-21 | Tag non-empty trimmed | Service validation | tags |
| BR-22 | EmotionEntry intensity 1–10 | CHECK `ck_emotion_entries_intensity` | emotion_entries |
| BR-23 | EmotionEntry context enum | CHECK `ck_emotion_entries_context` | emotion_entries |
| BR-24 | Attachment <= 10MB | Service validation at upload | attachments |
| BR-25 | Commission/swap DEFAULT 0 | `trades.commission` DEFAULT 0, `trades.swap_fees` DEFAULT 0 | Trade |
| BR-26 | Account name UNIQUE | UNIQUE INDEX `uq_accounts_name` | accounts |
| BR-27 | Account status enum | CHECK `ck_accounts_status` | accounts |
| BR-28 | TradingSession start <= end | Service validation | trading_sessions |
| BR-29 | Trade NEVER physically deleted | Service prohibits DELETE API; `is_active` + `status='archived'` | Trade |

### Constraint → Implementation

| Constraint | How Enforced |
|-----------|-------------|
| C1 — Audit fields | §4 every entity has `created_at`; mutable entities add `updated_at`; deletable entities add `is_active` |
| C2 — Surrogate keys | §4 every table: `id INTEGER PRIMARY KEY AUTOINCREMENT`. All logical keys (name, symbol) use UNIQUE indexes. |
| C3 — Explicit FK behavior | §6 every FK has declared ON DELETE (CASCADE / RESTRICT / SET NULL). No defaults. |
| C4 — Catalog classification | §7 seed data for markets, market_sessions, timeframes, emotions, mistakes — no `updated_at`, no `is_active` |
| C5 — Extensibility | §7 additive-only migrations. New entities add tables with `trade_id FK` — no existing table modification needed. |
| C6 — DB as implementation | §8 decision table. Physical decisions (REAL type, ISO 8601 text, index naming) never alter domain model. |

### Principle → Design Reflection

| Principle | How Reflected |
|-----------|--------------|
| **Canonical Trade** | Trade is the SSOT. §1 semantic spine: every module reads/writes Trade. No alternative trade representation. 9 FKs radiate from `trades`. |
| **Domain Governs DB** | §4 schema flows from domain model, not ORM. CHECK constraints mirror domain invariants. C6 enforced throughout. |
| **SSOT** | Single `trades` table. No cached/stored metrics. No redundant representations. Derived values computed on-the-fly. |
| **Domain Evolution Policy** | §9.1 — forward-compatible rules (never repurpose, never redefine, additive migrations, destructive changes need new SDD). |
| **Versioning** | §9.2 — backward data compatibility across versions. Breaking changes require data migration plan within the SDD. |
| **Canonical Dictionaries** | §9.3 — catalog entities are official dictionaries. Free-text duplication of catalog concepts prohibited. |
