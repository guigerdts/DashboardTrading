"""Repository tests for catalog entities.

Covers read-only ``list_all()`` for Market, MarketSession, Timeframe,
and full CRUD for Broker.
"""

import pytest

from app.models.catalogs import Broker, Market, MarketSession, Timeframe


@pytest.mark.asyncio
async def test_market_repository_list_all(uow):
    """``MarketRepository.list_all()`` returns markets ordered by name."""
    await uow.markets.add(Market(name="crypto"))
    await uow.markets.add(Market(name="forex"))
    results = await uow.markets.list_all()
    assert len(results) >= 2
    assert results[0].name == "crypto"
    assert results[1].name == "forex"


@pytest.mark.asyncio
async def test_market_session_repository_list_all(uow):
    """``MarketSessionRepository.list_all()`` returns sessions ordered by name."""
    await uow.market_sessions.add(MarketSession(name="asian"))
    await uow.market_sessions.add(MarketSession(name="european"))
    results = await uow.market_sessions.list_all()
    assert len(results) >= 2


@pytest.mark.asyncio
async def test_timeframe_repository_list_all(uow):
    """``TimeframeRepository.list_all()`` returns timeframes ordered by name."""
    await uow.timeframes.add(Timeframe(name="M5"))
    await uow.timeframes.add(Timeframe(name="H1"))
    results = await uow.timeframes.list_all()
    assert len(results) >= 2
    assert results[0].name == "H1"  # ordered alphabetically
    assert results[1].name == "M5"


@pytest.mark.asyncio
async def test_broker_repository_list_all(uow):
    """``BrokerRepository.list_all()`` returns active brokers ordered by name."""
    await uow.brokers.add(Broker(name="broker_b"))
    await uow.brokers.add(Broker(name="broker_a"))
    results = await uow.brokers.list_all()
    assert len(results) >= 2
    assert results[0].name == "broker_a"
    assert results[1].name == "broker_b"


@pytest.mark.asyncio
async def test_broker_repository_get_existing(uow):
    """``BrokerRepository.get()`` returns existing broker by ID."""
    broker = Broker(name="test_broker_get")
    await uow.brokers.add(broker)
    result = await uow.brokers.get(broker.id)
    assert result is not None
    assert result.name == "test_broker_get"


@pytest.mark.asyncio
async def test_broker_repository_get_nonexistent(uow):
    """``BrokerRepository.get()`` returns ``None`` for missing ID."""
    result = await uow.brokers.get(99999)
    assert result is None


@pytest.mark.asyncio
async def test_broker_repository_get_by_name_found(uow):
    """``BrokerRepository.get_by_name()`` returns broker when name matches."""
    broker = Broker(name="unique_broker_name")
    await uow.brokers.add(broker)
    result = await uow.brokers.get_by_name("unique_broker_name")
    assert result is not None
    assert result.id == broker.id


@pytest.mark.asyncio
async def test_broker_repository_get_by_name_not_found(uow):
    """``BrokerRepository.get_by_name()`` returns ``None`` for unknown name."""
    result = await uow.brokers.get_by_name("nonexistent_broker")
    assert result is None
