"""Endpoint tests for the assets module.

Covers all 5 routes: POST (create), GET (list + get), PATCH (update),
DELETE (soft-delete).
"""

import pytest

from app.models.catalogs import Market

# =========================================================================
# Helpers
# =========================================================================


@pytest.fixture
async def market(uow):
    """Create a Market fixture for asset endpoint tests."""
    m = Market(name="forex_endpoint")
    await uow.markets.add(m)
    return m


# =========================================================================
# POST /api/assets
# =========================================================================


@pytest.mark.asyncio
async def test_create_asset_201(client, market):
    """``POST /api/assets`` with valid data returns 201."""
    payload = {
        "symbol": "EURUSD",
        "name": "Euro/US Dollar",
        "market_id": market.id,
    }
    resp = await client.post("/api/assets", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["symbol"] == "EURUSD"
    assert data["name"] == "Euro/US Dollar"
    assert data["market_id"] == market.id
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_duplicate_409(client, market):
    """``POST /api/assets`` with duplicate (symbol, market_id) returns 409."""
    payload = {
        "symbol": "GBPUSD",
        "market_id": market.id,
    }
    resp1 = await client.post("/api/assets", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/assets", json=payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_missing_market_422(client):
    """``POST /api/assets`` with nonexistent market_id returns 422."""
    payload = {
        "symbol": "EURUSD",
        "market_id": 99999,
    }
    resp = await client.post("/api/assets", json=payload)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert isinstance(detail, list)
    assert any("does not exist" in err.get("msg", "").lower() for err in detail)


# =========================================================================
# GET /api/assets
# =========================================================================


@pytest.mark.asyncio
async def test_list_assets_200(client, market):
    """``GET /api/assets`` returns paginated response."""
    # Create two assets
    for symbol in ("EURUSD", "GBPUSD"):
        await client.post(
            "/api/assets",
            json={
                "symbol": symbol,
                "market_id": market.id,
            },
        )

    resp = await client.get("/api/assets")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_list_assets_with_symbol_filter(client, market):
    """``GET /api/assets?symbol=EURUSD`` filters by symbol (global)."""
    await client.post("/api/assets", json={"symbol": "EURUSD", "market_id": market.id})
    await client.post("/api/assets", json={"symbol": "GBPUSD", "market_id": market.id})

    resp = await client.get("/api/assets", params={"symbol": "EURUSD"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["symbol"] == "EURUSD"


# =========================================================================
# GET /api/assets/{id}
# =========================================================================


@pytest.mark.asyncio
async def test_get_asset_by_id_200(client, market):
    """``GET /api/assets/{id}`` returns the asset."""
    create_resp = await client.post(
        "/api/assets",
        json={
            "symbol": "USDJPY",
            "market_id": market.id,
        },
    )
    asset_id = create_resp.json()["id"]

    resp = await client.get(f"/api/assets/{asset_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == asset_id
    assert resp.json()["symbol"] == "USDJPY"


@pytest.mark.asyncio
async def test_get_asset_not_found_404(client):
    """``GET /api/assets/{id}`` with nonexistent ID returns 404."""
    resp = await client.get("/api/assets/99999")
    assert resp.status_code == 404


# =========================================================================
# PATCH /api/assets/{id}
# =========================================================================


@pytest.mark.asyncio
async def test_update_asset_200(client, market):
    """``PATCH /api/assets/{id}`` updates fields."""
    create_resp = await client.post(
        "/api/assets",
        json={
            "symbol": "AUDUSD",
            "market_id": market.id,
        },
    )
    asset_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/assets/{asset_id}",
        json={"name": "Australian Dollar/US Dollar"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Australian Dollar/US Dollar"


# =========================================================================
# DELETE /api/assets/{id}
# =========================================================================


@pytest.mark.asyncio
async def test_delete_asset_204(client, market):
    """``DELETE /api/assets/{id}`` returns 204 and soft-deletes."""
    create_resp = await client.post(
        "/api/assets",
        json={
            "symbol": "NZDUSD",
            "market_id": market.id,
        },
    )
    asset_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/assets/{asset_id}")
    assert resp.status_code == 204

    # Verify it's soft-deleted (is_active=False)
    get_resp = await client.get(f"/api/assets/{asset_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False
