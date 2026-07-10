# SDD Spec: Trade Context & Classification

**Change:** `trade-context-classification`
**Phase:** Spec
**Prerequisite:** Discovery D-01 through D-08
**Date:** 2026-07-09

---

## 1. API Contracts

### 1.1 Catalog CRUD (all four entities)

Each catalog (Strategy, Setup, Tag, Mistake) exposes the same REST pattern at `/api/{entity}`:

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| GET | `/api/strategies` | 200 | List active catalogs (`?archived=true` to include archived) |
| GET | `/api/strategies/{id}` | 200 / 404 | Single catalog element |
| POST | `/api/strategies` | 201 | Create new element |
| PATCH | `/api/strategies/{id}` | 200 / 404 | Update fields (name, description, etc.) |
| DELETE | `/api/strategies/{id}` | 200 | Soft-delete (sets `is_active=false`) |

Replace `strategies` with `setups`, `tags`, `mistakes` for each catalog.

**GET list query param:**
- `archived` (`bool`, default `false`) — when `true`, includes inactive elements

**DELETE behavior:**
- Always soft-delete (`is_active = false`)
- Returns the updated element with `is_active: false`

**Uniqueness constraints:**
- `name` is unique per catalog (Strategy, Setup, Tag, Mistake). POST/PATCH with a duplicate `name` → 409 Conflict.
- `name` comparison is case-insensitive. "Trend Following" and "trend following" conflict.
- Archived elements' names remain reserved (soft-deleted names cannot be reused for new active elements).

**Error codes summary:**

| Code | Condition |
|------|-----------|
| 404 | Element/trade not found |
| 409 | Duplicate `name` within catalog |
| 422 | Invalid field value, or reference to archived/non-existent element |

### 1.2 Tag assignment

```
PUT /api/trades/{id}/tags
Content-Type: application/json

{"tag_ids": [1, 5, 12]}
```

Replaces ALL tags for the trade (not additive). Sending `[]` clears all tags.

| Status | Condition |
|--------|-----------|
| 200 | Tags synced; returns `{ "tag_ids": [1, 5, 12] }` |
| 404 | Trade not found |
| 422 | Any `tag_id` references a non-existent or archived tag |

### 1.3 Mistake assignment

```
PUT /api/trades/{id}/mistakes
Content-Type: application/json

{
  "mistakes": [
    {"mistake_id": 3, "note": "Moved SL during news"},
    {"mistake_id": 5, "note": null}
  ]
}
```

Replaces ALL mistakes for the trade. Sending `[]` clears all.

| Status | Condition |
|--------|-----------|
| 200 | Mistakes synced; returns full list |
| 404 | Trade not found |
| 422 | Any `mistake_id` is non-existent or archived |

### 1.4 Extended trade detail

`GET /api/trades/{id}` (from v0.9) ADDED response fields:

```json
{
  "strategy": { "id": 1, "name": "Trend Following", "is_active": true } | null,
  "setup": { "id": 3, "name": "Bull Flag", "is_active": true } | null,
  "tags": [{"id": 1, "name": "London", "category": "session", "color": "#3B82F6", "is_active": true}],
  "mistakes": [
    {"mistake_id": 3, "name": "Moved SL", "note": "Moved SL during news", "is_active": true}
  ]
}
```

### 1.5 Extended trade update

`PATCH /api/trades/{id}` (from v0.9) ADDED accepted fields:

| Field | Type | Description |
|-------|------|-------------|
| `strategy_id` | `int \| null` | Assign strategy (null to clear) |
| `setup_id` | `int \| null` | Assign setup (null to clear) |

Returns 422 if `strategy_id`/`setup_id` references a non-existent or archived element.

---

## 2. Data Contracts (schemas)

### CatalogResponse

```python
class CatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None
    is_active: bool = True
    created_at: str
    updated_at: str | None = None
```

### TagResponse (extends CatalogResponse)

```python
class TagResponse(CatalogResponse):
    category: str | None = None
    color: str | None = None
```

### CatalogCreate / CatalogUpdate

```python
class CatalogCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None

class CatalogUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
```

Tags variant adds `category: str | None`, `color: str | None`.

### TagSync (request)

```python
class TagSyncRequest(BaseModel):
    tag_ids: list[int]
```

### MistakeSyncItem

```python
class MistakeSyncItem(BaseModel):
    mistake_id: int
    note: str | None = None

class MistakeSyncRequest(BaseModel):
    mistakes: list[MistakeSyncItem]
```

---

## 3. Use Cases (Given / When / Then)

### UC-01: Create catalog element

- GIVEN a user accesses the admin page for Strategies
- WHEN they submit a new strategy with name "Trend Following"
- THEN a new Strategy is created with `id`, `name="Trend Following"`, `is_active=true`
- AND it appears in the strategies list

### UC-02: Archive catalog element with existing references

- GIVEN Strategy "Trend Following" (`id=1`) is assigned to 5 trades
- WHEN a user archives it via `DELETE /api/strategies/1`
- THEN `is_active` is set to `false`
- AND the 5 trades still show "Trend Following" in their detail
- AND "Trend Following" no longer appears in the strategy selector for new/edit trades

### UC-03: Assign tags to a trade

- GIVEN Trade id=5 exists
- AND tags "London" (id=1) and "Range" (id=3) exist
- WHEN the user sends `PUT /api/trades/5/tags` with `{"tag_ids": [1, 3]}`
- THEN the response status is 200
- AND `GET /api/trades/5` returns `tags` containing both tags

### UC-04: Clear all mistakes from a trade

- GIVEN Trade id=5 has two mistakes assigned
- WHEN the user sends `PUT /api/trades/5/mistakes` with `{"mistakes": []}`
- THEN the response status is 200
- AND `GET /api/trades/5` returns `mistakes: []`

### UC-05: Assign archived catalog element returns 422

- GIVEN Tag "London" (id=1) is archived (`is_active=false`)
- WHEN the user sends `PUT /api/trades/5/tags` with `{"tag_ids": [1]}`
- THEN the response status is 422
- AND the error message indicates "Tag with id 1 is archived or does not exist"

### UC-06: Duplicate tag assignment is idempotent

- GIVEN Trade id=5 has tag id=1 assigned
- WHEN the user sends `PUT /api/trades/5/tags` with `{"tag_ids": [1]}`
- THEN the response status is 200
- AND `trade_tags` has exactly one row for (5, 1)

---

## 4. Acceptance Criteria

| ID | Description | Covered by |
|----|-------------|------------|
| AC-01 | CRUD create: POST creates with correct fields | UC-01 |
| AC-02 | CRUD read: GET returns element | Integration test |
| AC-03 | CRUD update: PATCH updates allowed fields | Integration test |
| AC-04 | CRUD archive: DELETE sets is_active=false, does NOT remove row | UC-02 |
| AC-05 | Archived elements excluded from default list | UC-02 |
| AC-06 | Archived elements still resolve in trade detail | UC-02 |
| AC-07 | Assign archived element → 422 | UC-05 |
| AC-08 | Tags sync replaces all, not additive | UC-03 |
| AC-09 | Mistakes sync with optional note | UC-03 |
| AC-10 | Clear all tags/mistakes by sending empty array | UC-04 |
| AC-11 | No duplicate pivot rows on re-assignment | UC-06 |
| AC-12 | NULL strategy_id/setup_id clears the assignment | UC-01 variant |
| AC-13 | Non-existent reference → 422 | UC-05 |
| AC-14 | All existing v0.9 trade tests pass | Regression suite |
| AC-15 | No N+1 query on trade detail with context | Test assertion |
