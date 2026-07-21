"""Amap adapter tests using HTTPX MockTransport."""

from datetime import date

import httpx
import pytest

from app.modules.providers.amap import AmapTravelProvider
from app.modules.providers.errors import ProviderResponseError
from app.modules.providers.models import GeoPoint


def response_for(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/v3/geocode/geo":
        return httpx.Response(200, json={
            "status": "1",
            "geocodes": [{
                "formatted_address": "四川省成都市武侯区武侯祠",
                "adcode": "510107",
                "location": "104.043390,30.645129",
            }],
        })
    if request.url.path == "/v5/place/text":
        return httpx.Response(200, json={
            "status": "1",
            "pois": [{
                "id": "B001",
                "name": "武侯祠",
                "address": "武侯祠大街231号",
                "type": "风景名胜",
                "location": "104.043390,30.645129",
            }],
        })
    if request.url.path == "/v3/weather/weatherInfo":
        return httpx.Response(200, json={
            "status": "1",
            "forecasts": [{
                "city": "成都",
                "casts": [{
                    "date": "2026-08-01",
                    "dayweather": "多云",
                    "nightweather": "阵雨",
                    "daytemp_float": "30.0",
                    "nighttemp_float": "23.0",
                    "daywind": "南",
                    "nightwind": "南",
                }],
            }],
        })
    if request.url.path == "/v5/direction/walking":
        return httpx.Response(200, json={
            "status": "1",
            "route": {"paths": [{
                "distance": "1200",
                "cost": {"duration": "900"},
                "steps": [{
                    "instruction": "向东步行",
                    "step_distance": "1200",
                    "cost": {"duration": "900"},
                    "polyline": "104.043,30.645;104.053,30.655",
                }],
            }]},
        })
    raise AssertionError(f"unexpected Amap path: {request.url.path}")


@pytest.fixture
def provider():
    client = httpx.AsyncClient(
        base_url="https://restapi.amap.com",
        transport=httpx.MockTransport(response_for),
    )
    return AmapTravelProvider("test-key", client=client)


@pytest.mark.asyncio
async def test_amap_parses_geocode_poi_weather_and_route(provider):
    point = await provider.geocode("武侯祠", "成都")
    pois = await provider.search_pois("成都", "文化")
    weather = await provider.weather("成都", date(2026, 8, 1))
    route = await provider.route(
        point.data,
        GeoPoint(lat=30.655, lng=104.053),
        mode="walking",
    )

    assert point.data.adcode == "510107"
    assert pois.data[0].name == "武侯祠"
    assert weather.data.day_temp_c == 30
    assert route.data.duration_s == 900
    assert len(route.data.polyline) == 2
    assert all(item.meta.provider == "amap" for item in (point, pois, weather, route))

    await provider.aclose()


@pytest.mark.asyncio
async def test_amap_converts_api_error_to_provider_error():
    async def error_response(request):
        return httpx.Response(200, json={"status": "0", "info": "INVALID_USER_KEY"})

    client = httpx.AsyncClient(
        base_url="https://restapi.amap.com",
        transport=httpx.MockTransport(error_response),
    )
    provider = AmapTravelProvider("bad-key", client=client)

    with pytest.raises(ProviderResponseError, match="INVALID_USER_KEY"):
        await provider.geocode("武侯祠", "成都")

    await provider.aclose()
