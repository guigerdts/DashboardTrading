# Technical Debt — Application Layer MVP

## MVP Scope
These are acceptable for MVP and targeted for post-MVP resolution.

| Item | Impact | Target |
|------|--------|--------|
| **Missing auth/authorization** | All endpoints are public; anyone with network access can read/write trades, accounts, assets | post-MVP |
| **No request rate limiting** | Endpoints vulnerable to brute-force or accidental high-frequency calls | post-MVP |
| **No request ID tracking** | Cannot correlate log entries to individual requests; debugging production issues is harder | post-MVP |
| **No structured logging configuration** | Uses plain `logging.getLogger(__name__)` per module; no JSON or structured format; no log level configuration from settings | post-MVP |
| **No pagination overflow protection** | `page=999999` with `page_size=100` passes default validation and executes a large offset query; no upper bound on page number | post-MVP |
| **No response compression** | All responses served uncompressed; larger paginated responses could benefit from gzip/brotli | post-MVP |
| **Health endpoint is minimal** | `GET /api/health` returns `{"status": "ok"}` without checking DB connectivity or dependency health | post-MVP |
| **`entry_datetime` stored as ISO strings in DB** | Trade and other datetime fields stored as TEXT in SQLite instead of a native datetime type; this is partly an SQLite limitation but complicates date-range queries | post-MVP |
| **Schema drift — removed FK constraints** | Alembic autogenerate detected 4 FK constraints defined in the existing migration that no longer exist in the SQLAlchemy models (`risk_profile_id`, `trading_session_id`, `setup_id`, `strategy_id` on `trades` table). Likely caused by model refactoring without a corresponding migration. Not production-critical since the constraints were `SET NULL` and the referenced tables still exist. | post-MVP |

## Post-MVP (Beyond MVP Scope)
Items explicitly deferred to future phases.

| Item | Impact | Notes |
|------|--------|-------|
| **Integration test with real database** | SQLite in-memory testing doesn't catch PostgreSQL/SQLite behavioral differences (e.g., constraint deferrability, type coercion) | Requires PostgreSQL test container in CI |
| **Service/UoW coupling** | Each endpoint creates its own UoW via `Depends(get_uow)`. If a future use case needs atomicity across multiple module operations in a single request, the current design doesn't support sharing a UoW across different services | Architectural invariant by design — one UoW per request is the intended pattern for MVP; multi-UoW coordination would need a saga pattern |
| **CORS configuration is localhost-only** | `cors_origins = ["http://localhost:5173"]` limits the frontend to dev mode only | Expects deployment config to override via settings environment variable |
| **`PaginatedResponse[T]` uses PEP 695 syntax** | Uses `class PaginatedResponse[T](BaseModel):` which requires Python 3.12+. The project already requires `>=3.12` so this is forward-compatible by design, but could cause issues if deployment uses an older Python | Not a bug — documented as a deliberate use of modern Python |
| **No DB-level pagination cursor support** | Offset-based pagination can be slow on large datasets; cursor-based would be more efficient for real-time trade lists | Trade module's `entry_datetime DESC` order is a good candidate for keyset pagination in a future iteration |
