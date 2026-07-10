"""Endpoint tests for catalog CRUD — Strategy, Setup, Tag, Mistake.

Covers:
- Create, read, update, archive (full CRUD) for all four entities
- Duplicate name → 409 Conflict
- Archived entities not returned in default list
- Archived entity resolution still works
"""

import pytest


# ── Shared helpers ───────────────────────────────────────────────────────

CATALOG_ENDPOINTS = [
    ("strategies", {"name": "Trend Following"}),
    ("setups", {"name": "Pin Bar"}),
    ("tags", {"name": "scalping", "category": "style", "color": "#FF0000"}),
    ("mistakes", {"name": "FOMO"}),
]


@pytest.mark.parametrize("endpoint,payload", CATALOG_ENDPOINTS)
@pytest.mark.asyncio
async def test_catalog_create_201(client, endpoint, payload):
    """POST /api/{endpoint} returns 201 with created entity."""
    resp = await client.post(f"/api/{endpoint}", json=payload)
    assert resp.status_code == 201, f"Failed to create {endpoint}: {resp.text}"
    data = resp.json()
    assert data["name"] == payload["name"]
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.parametrize("endpoint,payload", CATALOG_ENDPOINTS)
@pytest.mark.asyncio
async def test_catalog_create_duplicate_409(client, endpoint, payload):
    """POST /api/{endpoint} with duplicate name returns 409."""
    resp1 = await client.post(f"/api/{endpoint}", json=payload)
    assert resp1.status_code == 201, f"First create failed: {resp1.text}"

    resp2 = await client.post(f"/api/{endpoint}", json=payload)
    assert resp2.status_code == 409, f"Expected 409 for duplicate {endpoint}: {resp2.text}"


@pytest.mark.parametrize("endpoint,payload", CATALOG_ENDPOINTS)
@pytest.mark.asyncio
async def test_catalog_list_active_200(client, endpoint, payload):
    """GET /api/{endpoint}s returns active entities only."""
    # Create an entity
    create_resp = await client.post(f"/api/{endpoint}", json=payload)
    assert create_resp.status_code == 201
    entity_id = create_resp.json()["id"]

    # List should include it
    list_resp = await client.get(f"/api/{endpoint}")
    assert list_resp.status_code == 200
    ids = [item["id"] for item in list_resp.json()]
    assert entity_id in ids

    # Archive it
    await client.delete(f"/api/{endpoint}/{entity_id}")

    # List should no longer include it
    list_resp2 = await client.get(f"/api/{endpoint}")
    ids2 = [item["id"] for item in list_resp2.json()]
    assert entity_id not in ids2


@pytest.mark.parametrize("endpoint,payload", CATALOG_ENDPOINTS)
@pytest.mark.asyncio
async def test_catalog_get_by_id_200(client, endpoint, payload):
    """GET /api/{endpoint}s/{id} returns the entity."""
    create_resp = await client.post(f"/api/{endpoint}", json=payload)
    entity_id = create_resp.json()["id"]

    resp = await client.get(f"/api/{endpoint}/{entity_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == entity_id


@pytest.mark.parametrize("endpoint,payload", CATALOG_ENDPOINTS)
@pytest.mark.asyncio
async def test_catalog_get_not_found_404(client, endpoint, payload):
    """GET /api/{endpoint}s/{id} with nonexistent ID returns 404."""
    resp = await client.get(f"/api/{endpoint}/99999")
    assert resp.status_code == 404


@pytest.mark.parametrize("endpoint,payload", CATALOG_ENDPOINTS)
@pytest.mark.asyncio
async def test_catalog_update_200(client, endpoint, payload):
    """PATCH /api/{endpoint}s/{id} updates the entity."""
    create_resp = await client.post(f"/api/{endpoint}", json=payload)
    entity_id = create_resp.json()["id"]

    update_payload = {"name": f"Updated {payload['name']}"}
    resp = await client.patch(f"/api/{endpoint}/{entity_id}", json=update_payload)
    assert resp.status_code == 200
    assert resp.json()["name"] == update_payload["name"]


@pytest.mark.parametrize("endpoint,payload", CATALOG_ENDPOINTS)
@pytest.mark.asyncio
async def test_catalog_archive_204(client, endpoint, payload):
    """DELETE /api/{endpoint}s/{id} returns 204 and archives."""
    create_resp = await client.post(f"/api/{endpoint}", json=payload)
    entity_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/{endpoint}/{entity_id}")
    assert resp.status_code == 204

    # Verify archived
    get_resp = await client.get(f"/api/{endpoint}/{entity_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False


# ── Tag-specific tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tag_create_with_category_and_color(client):
    """POST /api/tags with category and color stores them."""
    payload = {
        "name": "momentum_tag",
        "category": "style",
        "color": "#00FF00",
    }
    resp = await client.post("/api/tags", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["category"] == "style"
    assert data["color"] == "#00FF00"


@pytest.mark.asyncio
async def test_tag_update_category_and_color(client):
    """PATCH /api/tags/{id} updates category and color."""
    create_resp = await client.post("/api/tags", json={"name": "test_tag"})
    tag_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/tags/{tag_id}",
        json={"category": "risk", "color": "#0000FF"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "risk"
    assert data["color"] == "#0000FF"


# ── Case-insensitive duplicate name ──────────────────────────────────────


@pytest.mark.asyncio
async def test_catalog_duplicate_name_case_insensitive_409(client):
    """POST /api/strategies with same name but different case returns 409."""
    await client.post("/api/strategies", json={"name": "Scalping"})
    resp = await client.post("/api/strategies", json={"name": "scalping"})
    assert resp.status_code == 409
