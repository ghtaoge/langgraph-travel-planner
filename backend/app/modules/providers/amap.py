"""Amap Web Service adapter for geocoding, POI, weather, and routes."""

from datetime import date, datetime, timezone
from typing import Literal

import httpx

from app.modules.providers.errors import (
    ProviderConfigurationError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.modules.providers.models import (
    GeoPoint,
    Poi,
    ProviderMeta,
    ProviderResult,
    RoutePlan,
    RouteStep,
    WeatherForecast,
)


def _number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _point(value: str, *, address: str = "", adcode: str = "") -> GeoPoint:
    try:
        lng, lat = value.split(",", maxsplit=1)
        return GeoPoint(lat=float(lat), lng=float(lng), address=address, adcode=adcode)
    except (AttributeError, TypeError, ValueError) as error:
        raise ProviderResponseError(f"invalid Amap location: {value!r}") from error


def _meta() -> ProviderMeta:
    return ProviderMeta(provider="amap", fetched_at=datetime.now(timezone.utc))


class AmapTravelProvider:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://restapi.amap.com",
        timeout_seconds: float = 8.0,
        client: httpx.AsyncClient | None = None,
    ):
        if not api_key:
            raise ProviderConfigurationError("AMAP_API_KEY is not configured")
        self.api_key = api_key
        self.client = client or httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)

    async def _request(self, path: str, **params) -> dict:
        params.update({"key": self.api_key, "output": "JSON"})
        try:
            response = await self.client.get(path, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnavailableError(f"Amap request failed: {path}") from error
        if payload.get("status") != "1":
            message = payload.get("info") or payload.get("infocode") or "unknown Amap error"
            raise ProviderResponseError(message)
        return payload

    async def geocode(self, address: str, city: str = "") -> ProviderResult[GeoPoint]:
        payload = await self._request("/v3/geocode/geo", address=address, city=city)
        geocodes = payload.get("geocodes") or []
        if not geocodes:
            raise ProviderResponseError(f"Amap geocode returned no result: {city}{address}")
        item = geocodes[0]
        return ProviderResult(
            data=_point(
                item.get("location", ""),
                address=item.get("formatted_address", address),
                adcode=item.get("adcode", ""),
            ),
            meta=_meta(),
        )

    async def search_pois(
        self, city: str, keyword: str, limit: int = 10
    ) -> ProviderResult[list[Poi]]:
        payload = await self._request(
            "/v5/place/text",
            keywords=keyword,
            region=city,
            city_limit="true",
            page_size=max(1, min(limit, 25)),
            show_fields="business",
        )
        pois = []
        for item in payload.get("pois") or []:
            location = item.get("location")
            if not location:
                continue
            distance = item.get("distance")
            pois.append(
                Poi(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    address=item.get("address") if isinstance(item.get("address"), str) else "",
                    category=item.get("type", ""),
                    location=_point(location, address=item.get("address", "")),
                    distance_m=int(_number(distance)) if distance not in (None, "") else None,
                )
            )
        return ProviderResult(data=pois, meta=_meta())

    async def weather(
        self, city: str, target_date: date
    ) -> ProviderResult[WeatherForecast]:
        geocode = await self.geocode(city, city)
        if not geocode.data.adcode:
            raise ProviderResponseError(f"Amap geocode returned no adcode: {city}")
        payload = await self._request(
            "/v3/weather/weatherInfo",
            city=geocode.data.adcode,
            extensions="all",
        )
        forecasts = payload.get("forecasts") or []
        casts = forecasts[0].get("casts", []) if forecasts else []
        selected = next((item for item in casts if item.get("date") == target_date.isoformat()), None)
        if selected is None and casts:
            selected = casts[0]
        if selected is None:
            raise ProviderResponseError(f"Amap weather returned no forecast: {city}")
        return ProviderResult(
            data=WeatherForecast(
                city=forecasts[0].get("city", city),
                date=date.fromisoformat(selected["date"]),
                day_weather=selected.get("dayweather", ""),
                night_weather=selected.get("nightweather", ""),
                day_temp_c=_number(selected.get("daytemp_float") or selected.get("daytemp"), None),
                night_temp_c=_number(
                    selected.get("nighttemp_float") or selected.get("nighttemp"), None
                ),
                day_wind=selected.get("daywind", ""),
                night_wind=selected.get("nightwind", ""),
            ),
            meta=_meta(),
        )

    async def route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        mode: Literal["walking", "driving"] = "walking",
    ) -> ProviderResult[RoutePlan]:
        payload = await self._request(
            f"/v5/direction/{mode}",
            origin=f"{origin.lng},{origin.lat}",
            destination=f"{destination.lng},{destination.lat}",
        )
        paths = (payload.get("route") or {}).get("paths") or []
        if not paths:
            raise ProviderResponseError(f"Amap route returned no path: {mode}")
        path = paths[0]
        steps = []
        polyline = []
        for item in path.get("steps") or []:
            cost = item.get("cost") or {}
            steps.append(
                RouteStep(
                    instruction=item.get("instruction", ""),
                    distance_m=int(_number(item.get("step_distance") or item.get("distance"))),
                    duration_s=int(_number(cost.get("duration") or item.get("duration"))),
                )
            )
            for coordinate in (item.get("polyline") or "").split(";"):
                if coordinate:
                    polyline.append(_point(coordinate))
        path_cost = path.get("cost") or {}
        return ProviderResult(
            data=RoutePlan(
                mode=mode,
                distance_m=int(_number(path.get("distance"))),
                duration_s=int(_number(path_cost.get("duration") or path.get("duration"))),
                polyline=polyline,
                steps=steps,
            ),
            meta=_meta(),
        )

    async def aclose(self) -> None:
        await self.client.aclose()
