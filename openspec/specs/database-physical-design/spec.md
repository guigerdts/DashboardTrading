# Database Physical Design Specification

## Purpose

SQLite DDL — tables, columns, types, constraints, defaults, naming, indexes, FK policies, and migration strategy. **Domain governs database: every schema decision flows from the domain model, not the ORM. The physical database is an implementation detail of the domain model; no physical design decision may alter the domain model (C6).**

## Requirements

### Requirement: Naming Conventions

Every database object MUST follow these rules:

| Element | Convention | Example |
|---------|-----------|---------|
| Tables | snake_case plural | `trades`, `trade_tags` |
| Columns | snake_case | `entry_price`, `exit_datetime` |
| PKs | `id` INTEGER PRIMARY KEY AUTOINCREMENT | `id` |
| FKs | `{singular}_id` | `asset_id`, `strategy_id` |
| Junction | `{a}_{b}` (alphabetical) | `strategy_setups` |
| UNIQUE | `uq_{table}_{cols}` | `uq_assets_symbol_market` |
| Index | `ix_{table}_{col}` | `ix_trades_entry_datetime` |
| CHECK | `ck_{table}_{col}` | `ck_trades_direction` |

**C2 — Surrogate keys only:** All PKs are `id INTEGER PRIMARY KEY AUTOINCREMENT`. Visible names (strategy name, tag name, asset symbol) are NEVER the primary key. They are protected by UNIQUE constraints on their own columns.

#### Scenario: FK naming

- GIVEN a column referencing `strategies`
- WHEN DDL is created
- THEN column MUST be named `strategy_id`

#### Scenario: Name is not PK

- GIVEN Strategy with name "Scalping Strategy"
- WHEN DDL is created
- THEN `strategies.id` is the PK, `strategies.name` has a UNIQUE constraint but is NOT the PK

### Requirement: Data Types

| Domain | SQLite Type | Notes |
|--------|-------------|-------|
| PK/FK | INTEGER | AUTOINCREMENT for PKs |
| Monetary | REAL | IEEE 64-bit float |
| Quantities | REAL | quantity, position_size |
| File size | INTEGER | bytes |
| Sort/intensity | INTEGER | sort_order, intensity |
| Boolean | INTEGER | 0/1 |
| Text | TEXT | All strings |
| Timestamps | TEXT | ISO 8601 UTC |
| Enums | TEXT + CHECK | StrEnum matches DB string |

#### Scenario: ISO 8601 timestamp

- GIVEN Trade created at 2026-07-06 15:30:00 UTC
- WHEN stored in `created_at`
- THEN value MUST be `2026-07-06T15:30:00.000Z`

#### Scenario: Enum consistency

- GIVEN `Direction.LONG = "long"` in Python
- WHEN Trade with direction='long' is persisted
- THEN both StrEnum.value and DB CHECK string match

### Requirement: Constraints

Per BR requirements tables in core-domain-model spec: NOT NULL for mandatory fields, DEFAULT for sensible defaults (commission=0, sort_order=0), CHECK for domain ranges (>0, BETWEEN 1 AND 10) and enum literals (IN 'long','short'), UNIQUE for entity identity.

Python StrEnum classes (Direction, TradeStatus, EmotionContext, AttachmentType) MUST have `.value` matching DB CHECK strings exactly.

#### Scenario: CHECK rejects out-of-range

- GIVEN EmotionEntry intensity = 11
- WHEN persisted
- THEN `ck_emotion_entries_intensity` rejects the row

#### Scenario: Case mismatch rejected

- GIVEN Trade direction = 'LONG'
- WHEN persisted
- THEN CHECK constraint rejects mismatched case

### Requirement: Index Strategy

| Type | Count | Pattern | Examples |
|------|-------|---------|---------|
| FK indexes | 14 | `ix_{table}_{fk}` | ix_trades_account_id, ix_trades_asset_id |
| Date range | 2 | `ix_{table}_{dt}` | ix_trades_entry_datetime, ix_trades_exit_datetime |
| Composite | 3 | `ix_{tbl}_{c1}_{c2}` | ix_trades_status_entry_datetime, ix_trades_asset_entry_datetime, ix_trades_strategy_entry_datetime |
| Direction | 1 | `ix_{tbl}_{col}` | ix_trades_direction |
| Junction inverse | 3 | `ix_{tbl}_{fk}` | ix_trade_tags_tag_id, ix_trade_emotions_emotion_id, ix_strategy_setups_setup_id |
| Unique integrity | 7 | `uq_{tbl}_{cols}` | uq_strategies_name, uq_assets_symbol_market, uq_setups_name, uq_emotions_name, uq_tags_name, uq_mistakes_name, uq_accounts_name |

#### Scenario: FK index used in JOIN

- GIVEN a query JOINing trades to assets on asset_id
- WHEN EXPLAIN query plan
- THEN `ix_trades_asset_id` MUST appear in the plan

#### Scenario: UNIQUE index prevents duplicates

- GIVEN existing Tag "scalping"
- WHEN inserting another Tag "scalping"
- THEN `uq_tags_name` raises UNIQUE violation

### Requirement: FK Enforcement (C3)

`PRAGMA foreign_keys = ON` MUST be set per SQLAlchemy connection via `@event.listens_for(engine, "connect")`. **C3 — Every FK declaration MUST explicitly state ON DELETE CASCADE, RESTRICT, or SET NULL. No implicit FK behavior allowed.** Cascade policies per core-domain-model entity relationships table.

#### Scenario: FK pragma on connect

- GIVEN a new SQLAlchemy connection
- WHEN connection is established
- THEN `PRAGMA foreign_keys` returns 1

### Requirement: Migration Strategy

Use Alembic autogenerate with `target_metadata = Base.metadata`. Seed lookup tables by name (stable identifier), not by ID.

#### Scenario: Seed by name

- GIVEN a seed migration for default emotions
- WHEN migration runs
- THEN emotion names ('fear', 'greed') are the stable reference — IDs are auto-incremented

#### Scenario: Autogenerate detects new column

- GIVEN a new column on Trade model
- WHEN `alembic revision --autogenerate`
- THEN migration contains ALTER TABLE ADD COLUMN

### Requirement: Database as Implementation (C6)

The SQLite schema is the physical implementation of the domain model, not its definition. No physical design decision (column type choice, index naming convention, storage optimization, or SQLite-specific feature) may alter the domain model's entities, relationships, business rules, or architectural principles defined in `core-domain-model`. If a physical constraint cannot be enforced at the DB level (e.g., SL/TP side validation), it MUST be enforced at the service layer — the domain rule still applies regardless of the enforcement mechanism.

#### Scenario: Service enforces domain rule not expressible in DDL

- GIVEN BR-07: "Stop loss MUST be on the correct side"
- WHEN implemented
- THEN if a CHECK constraint cannot validate the rule, a service-layer validation MUST enforce it — the rule is never weakened to match DB capabilities
