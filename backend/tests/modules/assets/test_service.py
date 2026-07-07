"""Service tests for the assets module.

Covers business rule enforcement (BR-16 symbol+market uniqueness, market
existence validation) for ``AssetService``.
"""

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.catalogs import Market
from app.modules.assets.schemas import AssetCreate, AssetUpdate
from app.modules.assets.service import AssetService


@pytest.fixture
def svc(uow) -> AssetService:
    """Create an ``AssetService`` backed by the test ``uow``."""
    return AssetService(uow)


# =========================================================================
# create()
# =========================================================================


@pytest.mark.asyncio
async def test_create_succeeds(svc, uow):
    """``create()`` with valid data returns the created asset."""
    market = Market(name="forex_create")
    await uow.markets.add(market)

    dto = AssetCreate(symbol="EURUSD", name="Euro/US Dollar", market_id=market.id)
    asset = await svc.create(dto)
    assert asset.id is not None
    assert asset.symbol == "EURUSD"
    assert asset.name == "Euro/US Dollar"
    assert asset.market_id == market.id
    assert asset.is_active == 1


@pytest.mark.asyncio
async def test_create_duplicate_raises_conflict(svc, uow):
    """``create()`` with duplicate ``(symbol, market_id)`` raises ``ConflictError`` (409)."""
    market = Market(name="forex_dup")
    await uow.markets.add(market)

    dto = AssetCreate(symbol="EURUSD", market_id=market.id)
    await svc.create(dto)

    with pytest.raises(ConflictError, match="already exists"):
        await svc.create(dto)


@pytest.mark.asyncio
async def test_create_missing_market_raises_business_rule(svc):
    """``create()`` with nonexistent market_id raises ``BusinessRuleError`` (422)."""
    dto = AssetCreate(symbol="EURUSD", market_id=99999)
    with pytest.raises(BusinessRuleError, match="does not exist"):
        await svc.create(dto)


# =========================================================================
# get()
# =========================================================================


@pytest.mark.asyncio
async def test_get_existing_returns_asset(svc, uow):
    """``get()`` returns the asset when it exists."""
    market = Market(name="forex_get_test")
    await uow.markets.add(market)

    dto = AssetCreate(symbol="EURUSD", market_id=market.id)
    created = await svc.create(dto)

    asset = await svc.get(created.id)
    assert asset.id == created.id
    assert asset.symbol == "EURUSD"


@pytest.mark.asyncio
async def test_get_nonexistent_raises_not_found(svc):
    """``get()`` with nonexistent ID raises ``NotFoundError`` (404)."""
    with pytest.raises(NotFoundError):
        await svc.get(99999)


# =========================================================================
# update()
# =========================================================================


@pytest.mark.asyncio
async def test_update_name_succeeds(svc, uow):
    """``update()`` changes the asset name."""
    market = Market(name="forex_upd_name")
    await uow.markets.add(market)

    dto = AssetCreate(symbol="EURUSD", market_id=market.id)
    asset = await svc.create(dto)

    update_dto = AssetUpdate(name="Updated Name")
    updated = await svc.update(asset.id, update_dto)
    assert updated.name == "Updated Name"


@pytest.mark.asyncio
async def test_update_duplicate_raises_conflict(svc, uow):
    """``update()`` with symbol taken by another asset raises ``ConflictError``."""
    market = Market(name="forex_upd_dup")
    await uow.markets.add(market)
    market2 = Market(name="crypto_upd_dup")
    await uow.markets.add(market2)

    # Create two assets in different markets
    await svc.create(AssetCreate(symbol="EURUSD", market_id=market.id))
    asset2 = await svc.create(AssetCreate(symbol="BTCUSD", market_id=market2.id))

    # Try to update asset2's symbol to EURUSD (same symbol, different market) — should be fine
    # Now try to update asset2's symbol AND market_id to match asset1
    update_dto = AssetUpdate(symbol="EURUSD", market_id=market.id)
    with pytest.raises(ConflictError, match="already exists"):
        await svc.update(asset2.id, update_dto)


# =========================================================================
# BR-29 — Soft delete
# =========================================================================


@pytest.mark.asyncio
async def test_soft_delete_sets_inactive(svc, uow):
    """``soft_delete()`` sets ``is_active=0``."""
    market = Market(name="forex_soft_del")
    await uow.markets.add(market)

    dto = AssetCreate(symbol="EURUSD", market_id=market.id)
    asset = await svc.create(dto)

    await svc.soft_delete(asset.id)

    deleted = await svc.get(asset.id)
    assert deleted.is_active == 0
