"""Provider cache and degradation behavior tests."""

from datetime import date, datetime, timezone

import pytest

from app.modules.providers.cache import MemoryProviderCache
from app.modules.providers.errors import ProviderUnavailableError
from app.modules.providers.mock import MockTravelProvider
from app.modules.providers.service import TravelDataService


class CountingProvider(MockTravelProvider):
    def __init__(self):
        self.geocode_calls = 0

    async def geocode(self, address: str, city: str = ""):
        self.geocode_calls += 1
        result = await super().geocode(address, city)
        result.meta.provider = "primary"
        result.meta.estimated = False
        result.meta.warnings = []
        return result


class FailingProvider(MockTravelProvider):
    async def geocode(self, address: str, city: str = ""):
        raise ProviderUnavailableError("primary offline")


@pytest.mark.asyncio
async def test_service_reuses_fresh_cache():
    primary = CountingProvider()
    service = TravelDataService(primary, MockTravelProvider(), MemoryProviderCache())

    first = await service.geocode("武侯祠", "成都")
    second = await service.geocode("武侯祠", "成都")

    assert primary.geocode_calls == 1
    assert first == second
    assert second.meta.provider == "primary"


@pytest.mark.asyncio
async def test_service_falls_back_with_explicit_warning():
    service = TravelDataService(FailingProvider(), MockTravelProvider(), MemoryProviderCache())

    result = await service.geocode("武侯祠", "成都")

    assert result.meta.provider == "mock"
    assert result.meta.estimated is True
    assert any("primary offline" in warning for warning in result.meta.warnings)


@pytest.mark.asyncio
async def test_service_caches_weather_independently_by_date():
    primary = MockTravelProvider()
    cache = MemoryProviderCache()
    service = TravelDataService(primary, MockTravelProvider(), cache)

    first = await service.weather("成都", date(2026, 8, 1))
    second = await service.weather("成都", date(2026, 8, 2))

    assert first.data.date != second.data.date
    assert len(cache.entries) == 2


@pytest.mark.asyncio
async def test_service_returns_stale_cache_before_mock_fallback():
    cache = MemoryProviderCache()
    service = TravelDataService(CountingProvider(), MockTravelProvider(), cache)
    fresh = await service.geocode("武侯祠", "成都")
    entry = next(iter(cache.entries.values()))
    entry.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    service.primary = FailingProvider()

    stale = await service.geocode("武侯祠", "成都")

    assert stale.data == fresh.data
    assert stale.meta.provider == "primary"
    assert stale.meta.stale is True
    assert any("primary offline" in warning for warning in stale.meta.warnings)
