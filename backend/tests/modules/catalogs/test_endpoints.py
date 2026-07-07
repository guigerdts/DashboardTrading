"""Endpoint tests for the catalogs module.

Covers:
- Read-only GET for Markets, MarketSessions, Timeframes
- Broker CRUD: list, get by ID, create, duplicate-name (BR-17)
"""

import pytest


@pytest.mark.asyncio
async def test_list_markets(client):
    """``GET /api/markets`` returns 200 with a list."""
    response = await client.get("/api/markets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_market_sessions(client):
    """``GET /api/market-sessions`` returns 200 with a list."""
    response = await client.get("/api/market-sessions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_timeframes(client):
    """``GET /api/timeframes`` returns 200 with a list."""
    response = await client.get("/api/timeframes")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_list_brokers(client):
    """``GET /api/brokers`` returns 200 with a list."""
    response = await client.get("/api/brokers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_broker_existing(client):
    """``GET /api/brokers/{id}`` returns 200 for an existing broker."""
    # Create a broker first
    create_resp = await client.post(
        "/api/brokers", json={"name": "get_broker_test"}
    )
    assert create_resp.status_code == 201
    broker_id = create_resp.json()["id"]

    # Retrieve by ID
    response = await client.get(f"/api/brokers/{broker_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "get_broker_test"
    assert data["id"] == broker_id


@pytest.mark.asyncio
async def test_get_broker_not_found(client):
    """``GET /api/brokers/{id}`` returns 404 for a missing broker."""
    response = await client.get("/api/brokers/99999")
    assert response.status_code == 404
    assert "not found" in response.text.lower()


@pytest.mark.asyncio
async def test_create_broker(client):
    """``POST /api/brokers`` creates a broker and returns 201."""
    response = await client.post(
        "/api/brokers", json={"name": "new_broker_test"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "new_broker_test"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_broker_duplicate_name(client):
    """``POST /api/brokers`` with duplicate name succeeds (BR-17)."""
    resp1 = await client.post(
        "/api/brokers", json={"name": "dup_broker_test"}
    )
    assert resp1.status_code == 201

    # Second broker with same name — should succeed with warning (BR-17)
    resp2 = await client.post(
        "/api/brokers", json={"name": "dup_broker_test"}
    )
    assert resp2.status_code == 201
    data = resp2.json()
    assert data["name"] == "dup_broker_test"
