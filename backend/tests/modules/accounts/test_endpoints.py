"""Endpoint tests for the accounts module.

Covers all 5 routes: POST (create), GET (list + get), PATCH (update),
DELETE (soft-delete).
"""

import pytest


@pytest.mark.asyncio
async def test_create_account_201(client):
    """``POST /api/accounts`` with valid data returns 201."""
    payload = {
        "name": "my_live_account",
        "broker": "InteractiveBrokers",
        "account_type": "live",
        "base_currency": "EUR",
    }
    resp = await client.post("/api/accounts", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "my_live_account"
    assert data["broker"] == "InteractiveBrokers"
    assert data["base_currency"] == "EUR"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_duplicate_name_409(client):
    """``POST /api/accounts`` with duplicate name returns 409."""
    payload = {"name": "duplicate_endpoint"}
    resp1 = await client.post("/api/accounts", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/api/accounts", json=payload)
    assert resp2.status_code == 409
    assert "already exists" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_accounts_200(client):
    """``GET /api/accounts`` returns paginated response."""
    # Create two accounts
    for i in range(2):
        await client.post("/api/accounts", json={
            "name": f"list_test_acc_{i}",
        })

    resp = await client.get("/api/accounts")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_get_account_by_id_200(client):
    """``GET /api/accounts/{id}`` returns the account."""
    create_resp = await client.post("/api/accounts", json={
        "name": "get_by_id_test",
    })
    account_id = create_resp.json()["id"]

    resp = await client.get(f"/api/accounts/{account_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == account_id
    assert resp.json()["name"] == "get_by_id_test"


@pytest.mark.asyncio
async def test_get_account_not_found_404(client):
    """``GET /api/accounts/{id}`` with nonexistent ID returns 404."""
    resp = await client.get("/api/accounts/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_account_200(client):
    """``PATCH /api/accounts/{id}`` updates fields."""
    create_resp = await client.post("/api/accounts", json={
        "name": "update_test_acc",
    })
    account_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/accounts/{account_id}",
        json={"broker": "UpdatedBroker", "status": "inactive"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["broker"] == "UpdatedBroker"
    assert data["status"] == "inactive"


@pytest.mark.asyncio
async def test_update_account_duplicate_name_409(client):
    """``PATCH /api/accounts/{id}`` with name taken by another returns 409."""
    await client.post("/api/accounts", json={"name": "existing_name_ep"})
    create_resp = await client.post("/api/accounts", json={"name": "another_ep"})
    account_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/accounts/{account_id}",
        json={"name": "existing_name_ep"},
    )
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_account_204(client):
    """``DELETE /api/accounts/{id}`` returns 204 and soft-deletes."""
    create_resp = await client.post("/api/accounts", json={
        "name": "delete_test_acc",
    })
    account_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/accounts/{account_id}")
    assert resp.status_code == 204

    # Verify it's soft-deleted (is_active=False)
    get_resp = await client.get(f"/api/accounts/{account_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False
