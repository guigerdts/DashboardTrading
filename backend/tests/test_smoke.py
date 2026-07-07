"""Smoke tests — verify app boots, routers are registered, and OpenAPI generates cleanly."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_app_creates_successfully():
    """Verify create_app() does not raise."""
    app = create_app()
    assert app is not None
    assert app.title is not None


def test_openapi_json_generates(client):
    """OpenAPI schema generates without errors."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "paths" in data
    # Verify all expected routers registered
    paths = data["paths"]
    assert "/api/markets" in paths
    assert "/api/market-sessions" in paths
    assert "/api/timeframes" in paths
    assert "/api/brokers" in paths
    assert "/api/trades" in paths
    assert "/api/accounts" in paths
    assert "/api/assets" in paths


def test_docs_page_loads(client):
    """Swagger UI docs render."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_all_expected_endpoints_present(client):
    """Verify every endpoint path from the spec is in OpenAPI."""
    response = client.get("/openapi.json")
    data = response.json()
    paths = data["paths"]

    expected = [
        # Catalogs
        ("/api/markets", "get"),
        ("/api/market-sessions", "get"),
        ("/api/timeframes", "get"),
        ("/api/brokers", "get"),
        ("/api/brokers/{id}", "get"),
        ("/api/brokers", "post"),
        # Trades
        ("/api/trades", "post"),
        ("/api/trades", "get"),
        ("/api/trades/{id}", "get"),
        ("/api/trades/{id}", "patch"),
        ("/api/trades/{id}", "delete"),
        ("/api/trades/{id}/close", "post"),
        # Accounts
        ("/api/accounts", "post"),
        ("/api/accounts", "get"),
        ("/api/accounts/{id}", "get"),
        ("/api/accounts/{id}", "patch"),
        ("/api/accounts/{id}", "delete"),
        # Assets
        ("/api/assets", "post"),
        ("/api/assets", "get"),
        ("/api/assets/{id}", "get"),
        ("/api/assets/{id}", "patch"),
        ("/api/assets/{id}", "delete"),
    ]

    for path, method in expected:
        assert path in paths, f"Missing endpoint: {method.upper()} {path}"
        assert method in paths[path], f"Missing method {method.upper()} for {path}"
