"""Provider protocols consumed by the application."""

from datetime import date
from typing import Literal, Protocol

from app.modules.providers.models import GeoPoint, Poi, ProviderResult, RoutePlan, WeatherForecast


class GeocodingProvider(Protocol):
    async def geocode(self, address: str, city: str = "") -> ProviderResult[GeoPoint]: ...


class PoiProvider(Protocol):
    async def search_pois(
        self, city: str, keyword: str, limit: int = 10
    ) -> ProviderResult[list[Poi]]: ...


class WeatherProvider(Protocol):
    async def weather(self, city: str, target_date: date) -> ProviderResult[WeatherForecast]: ...


class RouteProvider(Protocol):
    async def route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        mode: Literal["walking", "driving"] = "walking",
    ) -> ProviderResult[RoutePlan]: ...


class TravelProvider(GeocodingProvider, PoiProvider, WeatherProvider, RouteProvider, Protocol):
    async def aclose(self) -> None: ...
