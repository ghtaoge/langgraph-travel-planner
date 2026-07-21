"""Application lifecycle for the configured travel data service."""

from app.config.settings import settings
from app.modules.providers.amap import AmapTravelProvider
from app.modules.providers.cache import MemoryProviderCache, PostgresProviderCache
from app.modules.providers.mock import MockTravelProvider
from app.modules.providers.service import TravelDataService

_service: TravelDataService | None = None


async def init_travel_data_service(pool) -> TravelDataService:
    global _service
    fallback = MockTravelProvider()
    if settings.AMAP_API_KEY:
        primary = AmapTravelProvider(
            settings.AMAP_API_KEY,
            base_url=settings.AMAP_BASE_URL,
            timeout_seconds=settings.PROVIDER_TIMEOUT_SECONDS,
        )
    else:
        primary = fallback
    _service = TravelDataService(
        primary,
        fallback,
        PostgresProviderCache(pool),
        default_ttl_seconds=settings.PROVIDER_CACHE_TTL_SECONDS,
        weather_ttl_seconds=settings.WEATHER_CACHE_TTL_SECONDS,
    )
    return _service


def get_travel_data_service() -> TravelDataService:
    global _service
    if _service is None:
        fallback = MockTravelProvider()
        _service = TravelDataService(fallback, fallback, MemoryProviderCache())
    return _service


def set_travel_data_service(service: TravelDataService | None) -> None:
    global _service
    _service = service


async def close_travel_data_service() -> None:
    global _service
    if _service is not None:
        await _service.aclose()
        _service = None
