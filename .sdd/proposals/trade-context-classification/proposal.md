# Proposal: Trade Context & Classification

> **Prerequisite:** Discovery at `.sdd/discoveries/trade-context-classification/discovery.md`
> Domain model decisions D-01 through D-08 are binding and not re-litigated here.

## Intent

Complete the operational context of each Trade by adding Strategy, Setup, Tags, and Mistakes — the subjective layer that complements the objective data (execution, PnL, review) already built in v0.6–v0.9.

## Scope

### In Scope

**Backend**
- CRUD for Strategy, Setup, Tag, Mistake catalogs
- Pivot tables: `trade_tags`, `trade_mistakes` (with optional `note`)
- Extend `GET /api/trades/{id}` to return full context (strategy, setup, tags, mistakes)
- Extend `PATCH /api/trades/{id}` for strategy_id / setup_id updates
- Endpoints to sync tags (`PUT /api/trades/{id}/tags`) and mistakes (`PUT /api/trades/{id}/mistakes`)

**Frontend**
- Admin pages under `/settings/` for each catalog (strategies, setups, tags, mistakes)
- Replace placeholders in Trade Detail & Review with functional selectors
- Multi-select for Tags and Mistakes
- Single-select for Strategy and Setup

### Out of Scope
- Analytics, stats, dashboards, reports
- Auto-tagging, AI, recommendations
- Strategy → Setup hierarchy
- Strategy/Setup checklists
- Bulk operations
- Changes to MT5 Import, Trading Journal, or Analytics modules

## Capabilities

### New Capabilities
- `trade-context-catalogs`: CRUD admin for Strategy, Setup, Tag, Mistake
- `trade-context-assignment`: Assign/unassign context elements to/from a Trade

### Modified Capabilities
- `trade-review` (existing): Detail response gains context fields; review editor gains selectors for strategy, setup, tags, mistakes

## Approach

New tables for catalogs + pivots (no migration — new tables only). Extend existing trades service/repository to join context. Frontend admin pages follow the existing Settings page pattern. Context assignment uses React Query mutations that invalidate the detail query.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/app/models/` | New | `strategy.py`, `setup.py`, `tag.py`, `mistake.py` |
| `backend/app/modules/` | New | Catalog module with routers/services/repositories |
| `backend/app/modules/trades/` | Modify | Extend detail + patch endpoints for context |
| `frontend/src/modules/catalogs/` | New | Admin pages (strategies, setups, tags, mistakes) |
| `frontend/src/modules/trade-review/` | Modify | Replace placeholders with live selectors |
| `frontend/src/App.jsx` | Modify | Add `/settings/strategies`, `/settings/setups`, etc. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| N+1 on context joins in trade detail | Low | Eager-load via joinedload / selectinload |
| Route conflicts with existing `/settings` | Low | Settings already uses paths; add sub-routes |

## Rollback Plan

Revert catalog tables and pivot migrations. Trade detail falls back to pre-v0.10 behavior (no context). Frontend admin pages can be rolled back independently.

## Dependencies

- v0.9 Trade Detail & Review (must exist — serves as integration target)
- Discovery D-01 through D-08 (domain model decisions)

## Success Criteria

- [ ] Admin can create, rename, and archive strategies/setups/tags/mistakes from UI
- [ ] Trade Detail shows assigned context (strategy name, setup name, tags, mistakes)
- [ ] User can assign/change context from Trade Detail page
- [ ] Archived elements hidden from selectors but still render on existing trades
- [ ] All existing v0.9 tests still pass
