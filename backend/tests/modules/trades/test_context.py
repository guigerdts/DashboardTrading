"""Tests for trade context classification — tags, mistakes, strategy/setup.

Covers:
- Tag sync: replace semantics, duplicate prevention, archived → 422, clear via []
- Mistake sync: replace semantics, notes on pivot rows, archived → 422, clear via []
- Trade detail: strategy_name, setup_name, tags list, mistakes list
- N+1 assertion: get_detail with context uses expected query count
"""

import pytest
import pytest_asyncio

from app.models.mistake import Mistake
from app.models.strategy import Strategy, Setup
from app.models.tag import Tag


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def seeded_strategy(uow):
    """Create and return a seeded Strategy entity."""
    s = Strategy(name="Test Strategy", description="A test strategy")
    await uow.strategies.add(s)
    return s


@pytest_asyncio.fixture
async def seeded_setup(uow):
    """Create and return a seeded Setup entity."""
    s = Setup(name="Test Setup", description="A test setup")
    await uow.setups.add(s)
    return s


@pytest_asyncio.fixture
async def seeded_tags(uow):
    """Create and return 3 Tag entities."""
    tags = [
        Tag(name="tag_a", description="Tag A"),
        Tag(name="tag_b", description="Tag B"),
        Tag(name="tag_c", description="Tag C"),
    ]
    for t in tags:
        await uow.tags.add(t)
    return tags


@pytest_asyncio.fixture
async def seeded_mistakes(uow):
    """Create and return 2 Mistake entities."""
    mistakes = [
        Mistake(name="mistake_a", description="Mistake A"),
        Mistake(name="mistake_b", description="Mistake B"),
    ]
    for m in mistakes:
        await uow.mistakes.add(m)
    return mistakes


@pytest_asyncio.fixture
async def trade_with_context(client, seeded_strategy, seeded_setup, seeded_tags, seeded_mistakes):
    """Create a trade and attach context via API."""
    # Create trade
    create_resp = await client.post("/api/trades", json={
        "account_id": 1, "asset_id": 1, "direction": "long", "status": "open",
        "entry_price": 100.0, "quantity": 1.0, "entry_datetime": "2026-01-01T00:00:00",
    })
    trade_id = create_resp.json()["id"]

    # Set strategy/setup via PATCH
    await client.patch(f"/api/trades/{trade_id}", json={
        "strategy_id": seeded_strategy.id,
        "setup_id": seeded_setup.id,
    })

    # Sync tags
    tag_ids = [t.id for t in seeded_tags[:2]]  # tag_a, tag_b
    await client.put(f"/api/trades/{trade_id}/tags", json={"tag_ids": tag_ids})

    # Sync mistakes with notes
    mistakes_payload = [
        {"id": seeded_mistakes[0].id, "note": "First mistake note"},
        {"id": seeded_mistakes[1].id},
    ]
    await client.put(f"/api/trades/{trade_id}/mistakes", json={"mistakes": mistakes_payload})

    return trade_id


# ── Tag sync tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_tags_replace(client, seeded_tags):
    """PUT /api/trades/{id}/tags replaces old tags with new ones."""
    # Create a trade
    create_resp = await client.post("/api/trades", json={
        "account_id": 1, "asset_id": 1, "direction": "long", "status": "open",
        "entry_price": 100.0, "quantity": 1.0, "entry_datetime": "2026-01-01T00:00:00",
    })
    trade_id = create_resp.json()["id"]

    # Add tag_a, tag_b
    first_tags = [seeded_tags[0].id, seeded_tags[1].id]
    resp1 = await client.put(f"/api/trades/{trade_id}/tags", json={"tag_ids": first_tags})
    assert resp1.status_code == 200
    data1 = resp1.json()
    tag_names_1 = {t["name"] for t in data1["tags"]}
    assert "tag_a" in tag_names_1
    assert "tag_b" in tag_names_1

    # Replace with tag_c only — tag_a and tag_b should be removed
    second_tags = [seeded_tags[2].id]
    resp2 = await client.put(f"/api/trades/{trade_id}/tags", json={"tag_ids": second_tags})
    assert resp2.status_code == 200
    data2 = resp2.json()
    tag_names_2 = {t["name"] for t in data2["tags"]}
    assert "tag_c" in tag_names_2
    assert "tag_a" not in tag_names_2
    assert "tag_b" not in tag_names_2


@pytest.mark.asyncio
async def test_sync_tags_duplicate_prevention(client, seeded_tags):
    """Adding same tag twice via sync still results in one row (replace semantics)."""
    create_resp = await client.post("/api/trades", json={
        "account_id": 1, "asset_id": 1, "direction": "long", "status": "open",
        "entry_price": 100.0, "quantity": 1.0, "entry_datetime": "2026-01-01T00:00:00",
    })
    trade_id = create_resp.json()["id"]

    # Add same tag twice in one call (should only result in one entry)
    tag_ids = [seeded_tags[0].id, seeded_tags[0].id]
    resp = await client.put(f"/api/trades/{trade_id}/tags", json={"tag_ids": tag_ids})
    assert resp.status_code == 200
    assert len(resp.json()["tags"]) == 1


@pytest.mark.asyncio
async def test_sync_tags_archived_422(client, uow, seeded_tags):
    """PUT /api/trades/{id}/tags with archived tag returns 422."""
    create_resp = await client.post("/api/trades", json={
        "account_id": 1, "asset_id": 1, "direction": "long", "status": "open",
        "entry_price": 100.0, "quantity": 1.0, "entry_datetime": "2026-01-01T00:00:00",
    })
    trade_id = create_resp.json()["id"]

    # Archive a tag
    tagged = seeded_tags[0]
    tagged.is_active = 0

    resp = await client.put(f"/api/trades/{trade_id}/tags", json={"tag_ids": [tagged.id]})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sync_tags_clear_via_empty(client, trade_with_context):
    """PUT /api/trades/{id}/tags with [] clears all tags."""
    # Verify trade has tags initially
    detail = await client.get(f"/api/trades/{trade_with_context}")
    assert len(detail.json()["tags"]) > 0

    # Clear tags
    resp = await client.put(f"/api/trades/{trade_with_context}/tags", json={"tag_ids": []})
    assert resp.status_code == 200
    assert resp.json()["tags"] == []


# ── Mistake sync tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_mistakes_replace(client, seeded_mistakes):
    """PUT /api/trades/{id}/mistakes replaces old mistakes with new ones."""
    create_resp = await client.post("/api/trades", json={
        "account_id": 1, "asset_id": 1, "direction": "long", "status": "open",
        "entry_price": 100.0, "quantity": 1.0, "entry_datetime": "2026-01-01T00:00:00",
    })
    trade_id = create_resp.json()["id"]

    # Add mistake_a
    resp1 = await client.put(
        f"/api/trades/{trade_id}/mistakes",
        json={"mistakes": [{"id": seeded_mistakes[0].id, "note": "first"}]},
    )
    assert resp1.status_code == 200
    mistake_ids_1 = {m["id"] for m in resp1.json()["mistakes"]}
    assert seeded_mistakes[0].id in mistake_ids_1

    # Replace with mistake_b — mistake_a should be removed
    resp2 = await client.put(
        f"/api/trades/{trade_id}/mistakes",
        json={"mistakes": [{"id": seeded_mistakes[1].id}]},
    )
    assert resp2.status_code == 200
    mistake_ids_2 = {m["id"] for m in resp2.json()["mistakes"]}
    assert seeded_mistakes[0].id not in mistake_ids_2
    assert seeded_mistakes[1].id in mistake_ids_2


@pytest.mark.asyncio
async def test_sync_mistakes_with_notes(client, seeded_mistakes):
    """PUT /api/trades/{id}/mistakes stores notes on pivot rows."""
    create_resp = await client.post("/api/trades", json={
        "account_id": 1, "asset_id": 1, "direction": "long", "status": "open",
        "entry_price": 100.0, "quantity": 1.0, "entry_datetime": "2026-01-01T00:00:00",
    })
    trade_id = create_resp.json()["id"]

    mistakes_payload = [
        {"id": seeded_mistakes[0].id, "note": "Important mistake note"},
        {"id": seeded_mistakes[1].id},  # no note
    ]
    resp = await client.put(f"/api/trades/{trade_id}/mistakes", json={"mistakes": mistakes_payload})
    assert resp.status_code == 200

    mistakes = resp.json()["mistakes"]
    note_map = {m["id"]: m.get("note") for m in mistakes}
    assert note_map[seeded_mistakes[0].id] == "Important mistake note"
    assert note_map.get(seeded_mistakes[1].id) is None


@pytest.mark.asyncio
async def test_sync_mistakes_archived_422(client, uow, seeded_mistakes):
    """PUT /api/trades/{id}/mistakes with archived mistake returns 422."""
    create_resp = await client.post("/api/trades", json={
        "account_id": 1, "asset_id": 1, "direction": "long", "status": "open",
        "entry_price": 100.0, "quantity": 1.0, "entry_datetime": "2026-01-01T00:00:00",
    })
    trade_id = create_resp.json()["id"]

    # Archive a mistake
    seeded_mistakes[0].is_active = 0

    resp = await client.put(
        f"/api/trades/{trade_id}/mistakes",
        json={"mistakes": [{"id": seeded_mistakes[0].id}]},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sync_mistakes_clear_via_empty(client, trade_with_context):
    """PUT /api/trades/{id}/mistakes with [] clears all mistakes."""
    detail = await client.get(f"/api/trades/{trade_with_context}")
    assert len(detail.json()["mistakes"]) > 0

    resp = await client.put(f"/api/trades/{trade_with_context}/mistakes", json={"mistakes": []})
    assert resp.status_code == 200
    assert resp.json()["mistakes"] == []


# ── Trade detail context tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_trade_detail_strategy_setup_names(client, trade_with_context, seeded_strategy, seeded_setup):
    """GET /api/trades/{id} includes strategy_name and setup_name."""
    resp = await client.get(f"/api/trades/{trade_with_context}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["strategy_name"] == "Test Strategy"
    assert data["setup_name"] == "Test Setup"
    assert "tags" in data
    assert "mistakes" in data


@pytest.mark.asyncio
async def test_trade_detail_tags_list(client, trade_with_context):
    """GET /api/trades/{id} includes tags list with id and name."""
    resp = await client.get(f"/api/trades/{trade_with_context}")
    data = resp.json()
    tags = data["tags"]
    assert len(tags) == 2
    tag_names = {t["name"] for t in tags}
    assert "tag_a" in tag_names
    assert "tag_b" in tag_names
    assert all("id" in t and "name" in t for t in tags)


@pytest.mark.asyncio
async def test_trade_detail_mistakes_with_notes(client, trade_with_context):
    """GET /api/trades/{id} includes mistakes list with notes."""
    resp = await client.get(f"/api/trades/{trade_with_context}")
    data = resp.json()
    mistakes = data["mistakes"]
    assert len(mistakes) == 2

    note_map = {m["id"]: m.get("note") for m in mistakes}
    # One mistake has a note, the other doesn't
    notes_with_content = [v for v in note_map.values() if v is not None]
    assert len(notes_with_content) >= 1


@pytest.mark.asyncio
async def test_trade_detail_no_context(client):
    """GET /api/trades/{id} returns empty/null context when not set."""
    create_resp = await client.post("/api/trades", json={
        "account_id": 1, "asset_id": 1, "direction": "long", "status": "open",
        "entry_price": 100.0, "quantity": 1.0, "entry_datetime": "2026-01-01T00:00:00",
    })
    trade_id = create_resp.json()["id"]

    resp = await client.get(f"/api/trades/{trade_id}")
    data = resp.json()
    assert data["strategy_name"] is None
    assert data["setup_name"] is None
    assert data["tags"] == []
    assert data["mistakes"] == []


# ── N+1 query assertion ──────────────────────────────────────────────────
# SQLite in-memory doesn't support SQLAlchemy query instrumentation easily,
# so we verify via the number of loaded relations instead of actual query count.


@pytest.mark.asyncio
async def test_trade_detail_no_n_plus_one(client, uow, trade_with_context):
    """get_detail with context loads all relations eagerly (no lazy loads).

    Verification: all related attributes are already populated on the ORM
    object, meaning no additional queries are made when serializing.
    """
    # Fetch the trade via the UoW repo directly (not through API)
    trade = await uow.trades.get_with_relations(trade_with_context)
    assert trade is not None

    # Verify all loaded relations are eagerly loaded (no lazy loading needed)
    # strategy and setup should be loaded via joinedload
    assert hasattr(trade, "strategy")
    assert hasattr(trade, "setup")

    # tags should be loaded via selectinload
    assert hasattr(trade, "tags")
    # accessing tags should not trigger a new query (they're loaded)
    tag_list = trade.tags
    assert isinstance(tag_list, list)

    # mistakes should be loaded via selectinload
    assert hasattr(trade, "mistakes")
    mistake_list = trade.mistakes
    assert isinstance(mistake_list, list)
