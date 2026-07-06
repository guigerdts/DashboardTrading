# Core Domain Model Specification

## Purpose

19 entities, relationships, and 29 business rules (BR-01–BR-29). **Trade is the SSOT — no module creates an alternative trade representation.** The entity-relationship model and business rules GOVERN the physical database design, not the reverse (C6).

## Requirements

### Requirement: Entity Definition

The system MUST implement 19 entities with these constraints:

| Entity | Owner | Key Constraints |
|--------|-------|-----------------|
| Trade | trading_journal | Never deleted (BR-29). FKs to 15 tables |
| Account | trading_journal | Trade MUST have one. Account name UNIQUE |
| Asset | trading_journal | Belongs to Market. symbol+market UNIQUE |
| Market | trading_journal | Asset class lookup. Seeded |
| Broker | trading_journal | Nullable FK on Trade. Name SHOULD be UNIQUE |
| MarketSession, Timeframe | trading_journal | Nullable FKs on Trade. Seeded lookups |
| TradingSession | trading_journal | Manual start/end. Groups trades |
| Strategy | strategies | Nullable FK on Trade. Name UNIQUE |
| Setup | setups | Nullable FK on Trade. Name UNIQUE |
| RiskProfile | risk_management | Config only — never stores computed metrics |
| Emotion, EmotionEntry | psychology | intensity 1-10, context before/during/after |
| Tag, TradeTag | trading_journal | Tag UNIQUE. Junction: Trade <-> Tag |
| Mistake, MistakeEntry | error_management | Mistake UNIQUE. Entry records per Trade |
| Note | trading_journal | Inline note on Trade |
| TradeReview | trading_journal | Structured review. Rating columns reserved nullable |
| Attachment | screenshot_library | Type discriminator (MVP=image, extensible) |

**C1 — Audit fields per entity:**

| Entity | `created_at` | `updated_at` | `is_active` | Notes |
|--------|:---:|:---:|:---:|-------|
| Trade | YES | YES | YES | Soft-delete via is_active. updated_at stops at 30d post-close (soft-lock) |
| Account | YES | YES | YES | Deactivation via is_active |
| Asset | YES | YES | YES | Soft-remove via is_active |
| Market | YES | NO | NO | Seeded catalog — read-only after seed |
| Broker | YES | YES | YES | User-defined catalog |
| MarketSession | YES | NO | NO | Seeded catalog — read-only after seed |
| Timeframe | YES | NO | NO | Seeded catalog — read-only after seed |
| Strategy | YES | YES | YES | User-defined |
| Setup | YES | YES | YES | User-defined |
| RiskProfile | YES | YES | YES | Config presets |
| TradingSession | YES | YES | YES | User-defined sessions |
| Emotion | YES | NO | NO | Seeded catalog — immutable names |
| Tag | YES | NO | NO | Unique name. No soft-delete, just removal from junction |
| Mistake | YES | NO | NO | Seeded catalog — immutable names |
| EmotionEntry | YES | NO | NO | Transactional — no updates, no soft-delete |
| MistakeEntry | YES | NO | NO | Transactional — no updates, no soft-delete |
| TradeTag | YES | NO | NO | Junction — no soft-delete |
| Note | YES | YES | NO | Editable content, non-deletable |
| TradeReview | YES | YES | NO | Editable review, non-deletable |
| Attachment | YES | NO | YES | Soft-remove via is_active to avoid file leak |

**C4 — Catalog classification:**

| Entity | Editable | Notes |
|--------|----------|-------|
| Market | Protected | Seeded by system. Immutable after seed |
| MarketSession | Protected | Seeded by system. Immutable after seed |
| Timeframe | Protected | Seeded by system. Immutable after seed |
| Emotion | Protected | Seeded by system. Names immutable |
| Mistake | Protected | Seeded by system. Names immutable |
| Tag | Fully editable | User creates, renames, deletes freely |
| Asset | Partially editable | User adds assets. symbol+market pair immutable after creation |
| Broker | Fully editable | User defines brokers freely |
| Strategy | Fully editable | User creates, modifies, deactivates |
| Setup | Fully editable | User creates, modifies, deactivates |
| RiskProfile | Fully editable | User defines risk presets |

#### Scenario: Required trade fields

- GIVEN Trade creation
- WHEN persisted
- THEN asset_id, account_id, direction, entry_price>0, quantity>0, entry_datetime MUST be set

### Requirement: Entity Relationships (C3)

**C3 — Every FK relationship MUST explicitly define its on-delete behavior: CASCADE, RESTRICT, or SET NULL. No implicit or default behavior allowed.**

| Parent | Child | Card | On Delete | Nullable |
|--------|-------|------|-----------|----------|
| Account | Trade | 1:N | RESTRICT | — |
| Asset | Trade | 1:N | RESTRICT | — |
| Broker/MarketSession/Timeframe | Trade | 1:N | SET NULL | Yes |
| Strategy/Setup/RiskProfile/TradingSession | Trade | 1:N | SET NULL | Yes |
| Trade | EmotionEntry/MistakeEntry/Attachment/Note/TradeReview/TradeTag | 1:N | CASCADE | — |
| Emotion/Mistake/Tag | entry/trade_tag | 1:N | RESTRICT | — |
| Strategy | Setup | M:N | CASCADE | — |

#### Scenario: Restrict prevents asset deletion

- GIVEN Asset with 5 Trades
- WHEN DELETE attempted
- THEN FK violation raised, Asset persists

### Requirement: Business Rules (BR-01 to BR-29)

**Trade invariants (BR-01–13):** asset_id NOT NULL [DB], direction('long','short') [DB], quantity>0 [DB], entry_price>0 [DB], entry_datetime NOT NULL [DB], account_id NOT NULL [DB], SL correct side [Svc], TP correct side [Svc], SL/TP opposite [Svc], exit pair consistency [Svc], status('open','closed') [DB], 30-day soft-lock [Svc], position_size>=0 [DB].

**Entity invariants (BR-14–28):** Strategy name UNIQUE [DB], Setup name UNIQUE [DB], Asset(symbol,market_id) UNIQUE [DB], Broker name SHOULD UNIQUE [Svc], Emotion UNIQUE [DB], Tag UNIQUE [DB], Mistake UNIQUE [DB], Tag non-empty trimmed [Svc], EmotionEntry intensity 1-10 [DB], EmotionEntry context IN('before_entry','during_trade','after_exit') [DB], Attachment <=10MB [Svc], Commission/swap DEFAULT 0 [DB], Account name UNIQUE [DB], Account status('active','inactive') [DB], TradingSession start<=end [Svc].

**Immutability (BR-29):** Trade NEVER physically deleted. Status transition to 'archived' only. All relations preserved. [Service — no DELETE API, no DELETE SQL]

#### Scenario: Invalid direction

- GIVEN direction = 'invalid'
- WHEN persisted
- THEN DB CHECK rejects write

#### Scenario: Soft-delete preserves data

- GIVEN Trade with 2 Notes, 1 Attachment
- WHEN status -> 'archived'
- THEN Trade row + all relations remain queryable

#### Scenario: Duplicate tag

- GIVEN existing Tag "scalping"
- WHEN another Tag "scalping" created
- THEN UNIQUE violation raised

### Requirement: Extensibility (C5)

New entities related to Trade MUST be addable without modifying existing table structures. The domain model must remain extensible through additive changes only — new junction tables, new dependent entities (1:N from Trade), or new FK columns on Trade (nullable, additive migration). No structural refactoring of existing tables is required to introduce new domain concepts related to a trade.

#### Scenario: New trade-related entity

- GIVEN a new domain concept "TradeChecklist" related to Trade
- WHEN added to the model
- THEN `checklist_items` table with `trade_id FK` can be added without modifying `trades` or any other existing table
