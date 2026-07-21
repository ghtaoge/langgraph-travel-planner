"""Deterministic fallback provider used for development and degradation."""

import hashlib
import math
from datetime import date, datetime, timezone
from typing import Literal

from app.modules.providers.models import (
    GeoPoint,
    Poi,
    ProviderMeta,
    ProviderResult,
    RoutePlan,
    RouteStep,
    WeatherForecast,
)

CITY_CENTERS = {
    "成都": (30.5728, 104.0668, "510100"),
    "北京": (39.9042, 116.4074, "110100"),
    "上海": (31.2304, 121.4737, "310100"),
    "西安": (34.3416, 108.9398, "610100"),
    "重庆": (29.5630, 106.5516, "500100"),
}

CITY_POIS = {
    "成都": ["武侯祠", "杜甫草堂", "成都大熊猫繁育研究基地", "宽窄巷子"],
    "北京": ["故宫博物院", "颐和园", "天坛公园", "八达岭长城"],
    "西安": ["秦始皇兵马俑", "陕西历史博物馆", "西安城墙", "大雁塔"],
}


def _meta() -> ProviderMeta:
    return ProviderMeta(
        provider="mock",
        fetched_at=datetime.now(timezone.utc),
        confidence=0.45,
        estimated=True,
        warnings=["使用估算数据，未连接实时旅行数据服务"],
    )


def _stable_offset(value: str) -> tuple[float, float]:
    digest = hashlib.sha256(value.encode("utf-8")).digest()
    lat_offset = (int.from_bytes(digest[:2], "big") / 65535 - 0.5) * 0.08
    lng_offset = (int.from_bytes(digest[2:4], "big") / 65535 - 0.5) * 0.08
    return lat_offset, lng_offset


def _distance_m(origin: GeoPoint, destination: GeoPoint) -> int:
    radius = 6_371_000
    lat1, lat2 = math.radians(origin.lat), math.radians(destination.lat)
    delta_lat = math.radians(destination.lat - origin.lat)
    delta_lng = math.radians(destination.lng - origin.lng)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    )
    return round(radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value)))


class MockTravelProvider:
    async def geocode(self, address: str, city: str = "") -> ProviderResult[GeoPoint]:
        center = CITY_CENTERS.get(city, (31.2304, 121.4737, ""))
        lat_offset, lng_offset = _stable_offset(f"{city}:{address}")
        return ProviderResult(
            data=GeoPoint(
                lat=center[0] + lat_offset,
                lng=center[1] + lng_offset,
                address=f"{city}{address}",
                adcode=center[2],
            ),
            meta=_meta(),
        )

    async def search_pois(
        self, city: str, keyword: str, limit: int = 10
    ) -> ProviderResult[list[Poi]]:
        names = CITY_POIS.get(city, [f"{city}{keyword}景点{i}" for i in range(1, 5)])
        pois = []
        for index, name in enumerate(names[:limit]):
            point = (await self.geocode(name, city)).data
            pois.append(
                Poi(
                    id=f"mock-{hashlib.sha1(f'{city}:{name}'.encode()).hexdigest()[:12]}",
                    name=name,
                    address=point.address,
                    category=keyword or "旅游景点",
                    location=point,
                )
            )
        return ProviderResult(data=pois, meta=_meta())

    async def weather(
        self, city: str, target_date: date
    ) -> ProviderResult[WeatherForecast]:
        seed = int(hashlib.sha1(f"{city}:{target_date}".encode()).hexdigest()[:4], 16)
        conditions = ["晴", "多云", "阴", "阵雨"]
        day_temp = 22 + seed % 10
        return ProviderResult(
            data=WeatherForecast(
                city=city,
                date=target_date,
                day_weather=conditions[seed % len(conditions)],
                night_weather=conditions[(seed + 1) % len(conditions)],
                day_temp_c=day_temp,
                night_temp_c=day_temp - 6,
            ),
            meta=_meta(),
        )

    async def route(
        self,
        origin: GeoPoint,
        destination: GeoPoint,
        mode: Literal["walking", "driving"] = "walking",
    ) -> ProviderResult[RoutePlan]:
        distance = _distance_m(origin, destination)
        speed_mps = 1.25 if mode == "walking" else 8.33
        duration = round(distance / speed_mps) if distance else 0
        return ProviderResult(
            data=RoutePlan(
                mode=mode,
                distance_m=distance,
                duration_s=duration,
                polyline=[origin, destination],
                steps=[
                    RouteStep(
                        instruction=f"估算{mode}路线",
                        distance_m=distance,
                        duration_s=duration,
                    )
                ],
            ),
            meta=_meta(),
        )

    async def aclose(self) -> None:
        return None
