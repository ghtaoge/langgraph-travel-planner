"""Cached provider facade with stale-cache and Mock degradation."""

from collections.abc import Awaitable, Callable
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel

from app.modules.providers.cache import ProviderCache, cache_key
from app.modules.providers.contracts import TravelProvider
from app.modules.providers.errors import ProviderError
from app.modules.providers.models import (
    GeoPoint,
    Poi,
    ProviderResult,
    RoutePlan,
    WeatherForecast,
)


class TravelDataService:
    def __init__(
        self,
        primary: TravelProvider,
        fallback: TravelProvider,
        cache: ProviderCache,
        *,
        default_ttl_seconds: int = 3600,
        weather_ttl_seconds: int = 1800,
    ):
        self.primary = primary
        self.fallback = fallback
        self.cache = cache
        self.default_ttl_seconds = default_ttl_seconds
        self.weather_ttl_seconds = weather_ttl_seconds

    async def _load(
        self,
        *,
        data_type: str,
        parameters: dict,
        result_model: type[BaseModel],
        primary_call: Callable[[], Awaitable[ProviderResult]],
        fallback_call: Callable[[], Awaitable[ProviderResult]],
        ttl_seconds: int,
    ):
        key = cache_key(data_type, parameters)
        cached = await self.cache.get(key)
        now = datetime.now(timezone.utc)
        if cached and not cached.is_stale(now):
            return result_model.model_validate(cached.payload)

        try:
            result = await primary_call()
            await self.cache.set(key, data_type, result, ttl_seconds)
            return result
        except ProviderError as error:
            warning = f"主数据源不可用: {error}"
            if cached:
                result = result_model.model_validate(cached.payload)
                result.meta.stale = True
                result.meta.warnings.append(warning)
                return result
            result = await fallback_call()
            result.meta.estimated = True
            result.meta.warnings.append(warning)
            await self.cache.set(key, data_type, result, ttl_seconds)
            return result

    async def geocode(self, address: str, city: str = "") -> ProviderResult[GeoPoint]:
        return await self._load(
            data_type="geocode",
            parameters={"address": address, "city": city},
            result_model=ProviderResult[GeoPoint],
            primary_call=lambda: self.primary.geocode(address, city),
            fallback_call=lambda: self.fallback.geocode(address, city),
            ttl_seconds=self.default_ttl_seconds,
        )

    async def search_pois(
        self, city: str, keyword: str, limit: int = 10
    ) -> ProviderResult[list[Poi]]:
        return await self._load(
            data_type="poi",
            parameters={"city": city, "keyword": keyword, "limit": limit},
            result_model=ProviderResult[list[Poi]],
            primary_call=lambda: self.primary.search_pois(city, keyword, limit),
            fallback_call=lambda: self.fallback.search_pois(city, keyword, limit),
            ttl_seconds=self.default_ttl_seconds,
        )

    async def weather(
        self, city: str, target_date: date
    ) -> ProviderResult[WeatherForecast]:
        return await self._load(
            data_type="weather",
            parameters={"city": city, "date": target_date.isoformat()},
            result_model=ProviderResult[WeatherForecast],
            primary_call=lambda: self.primary.weather(city, target_date),
            fallback_call=lambda: self.fallback.weather(city, target_date),
            ttl_seconds=self.weather_ttl_seconds,
        )

    async def route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        mode: Literal["walking", "driving"] = "walking",
    ) -> ProviderResult[RoutePlan]:
        parameters = {
            "origin": [origin.lng, origin.lat],
            "destination": [destination.lng, destination.lat],
            "mode": mode,
        }
        return await self._load(
            data_type="route",
            parameters=parameters,
            result_model=ProviderResult[RoutePlan],
            primary_call=lambda: self.primary.route(origin, destination, mode),
            fallback_call=lambda: self.fallback.route(origin, destination, mode),
            ttl_seconds=self.default_ttl_seconds,
        )

    async def aclose(self) -> None:
        await self.primary.aclose()
        if self.fallback is not self.primary:
            await self.fallback.aclose()
