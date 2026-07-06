# Proposal: TIP Core Domain Model

## Intent

No domain model exists. Defines canonical entities, relationships, BRs, ER, and SQLite physical design that every future feature builds on. **Trade is the canonical entity of the system — all modules depend on it directly or indirectly.**

## Scope

### In Scope
- 19 entities, relationships, 29 BRs (BR-01–BR-29)
- ER: single wide trade table, FK cascade policies
- SQLite schema: tables, columns, types, constraints, defaults
- Index strategy (14 FK + 5 composite + 7 unique)
- Alembic migration plan + seed data, naming conventions

### Out of Scope
- FastAPI, React, CRUD, SQLAlchemy, Pydantic, repos, services
- AI/ML, brokers, backtesting, imports/exports

## Capabilities

### New Capabilities
- `core-domain-model`: Entities, relationships, BRs. What exists, optional, immutable.
- `database-physical-design`: SQLite DDL — columns, types, constraints, FK policies, indexes, naming, timestamps, enums, seed data. Drives all SQLAlchemy models.

### Modified Capabilities
None — existing specs are infrastructure-only.

## Approach

Single wide `trades` + FKs to 9 lookups. Junction M:N tables. File-paths for attachments. Metrics on-the-fly. RiskProfile = config only. Soft-delete (BR-29). Soft-lock at 30 days. **Domain governs database.** **Trade is the canonical entity — all modules depend on it directly or indirectly. No module may create an alternative trade representation.**

| Decision | Choice |
|----------|--------|
| Canonical Trade | Trade is the SSOT. All modules depend on it. No alternative trade representation allowed. |
| Account | Central, mandatory FK. Multi-account ready. |
| TradeReview | Structured entity. Rating columns reserved nullable for future. |
| Attachment type | Discriminator column. MVP=image, extensible. |
| TradingSession | Manual start/end. User creates + assigns. |
| RiskProfile | Config-only. Zero stored metrics. |
| Soft-delete (BR-29) | Never physically deleted. Archived only. |

## Affected Areas

| Area | Impact |
|------|--------|
| `openspec/specs/core-domain-model/spec.md` | New |
| `openspec/specs/database-physical-design/spec.md` | New |
| `backend/app/database.py` | Modify — add Base + FK pragma |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| FK pragma not set per connection | Med | `@event.listens_for` + test |
| REAL precision for money | Low | Decimal → float. IEEE 64-bit sufficient |
| Trade schema changes costly at scale | Med | Additive migrations. Get right in design. |
| Seed data ID conflicts | Low | Seed by name, not ID |

## Rollback Plan

Spec/docs only — no schema deployed. `git rm -r openspec/specs/core-domain-model/ openspec/specs/database-physical-design/` + revert `database.py`. Zero data risk.

## Dependencies

`base-architecture` spec. SQLite 3.x, Python 3.12+, SQLAlchemy 2.x.

## Success Criteria

- [ ] 19 entities with module ownership, FK policies
- [ ] 29 BRs with enforcement strategy (constraint / service / both)
- [ ] ER complete: cardinalities, cascade rules, on-delete
- [ ] SQLite schema: every table, column, type, constraint, default
- [ ] All indexes defined (FK, composite, unique) with naming
- [ ] Migration plan: Alembic autogenerate + seed data
- [ ] Canonical Trade: no module creates alternative trade representation. SSOT principle enforced.
- [ ] User-approved adjustments: Account central, TradeReview extensible, Attachment discriminator, TradingSession manual, RiskProfile config-only, soft-delete BR-29, Domain Governs DB
