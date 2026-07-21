"""Travel data provider contract tests."""

from datetime import date, datetime, timezone

from app.modules.providers.models import (
    GeoPoint,
    Poi,
    ProviderMeta,
    ProviderResult,
    RoutePlan,
    RouteStep,
    WeatherForecast,
)


def meta(**overrides) -> ProviderMeta:
    values = {
        "provider": "amap",
        "fetched_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return ProviderMeta(**values)


def test_provider_result_serializes_source_and_freshness():
    result = ProviderResult[GeoPoint](
        data=GeoPoint(lat=30.5728, lng=104.0668, address="成都市", adcode="510100"),
        meta=meta(confidence=0.9),
    )

    payload = result.model_dump(mode="json")

    assert payload["data"]["adcode"] == "510100"
    assert payload["meta"]["provider"] == "amap"
    assert payload["meta"]["stale"] is False
    assert payload["meta"]["estimated"] is False


def test_route_plan_keeps_geometry_and_steps():
    route = RoutePlan(
        mode="walking",
        distance_m=1200,
        duration_s=900,
        polyline=[GeoPoint(lat=30.5, lng=104.0), GeoPoint(lat=30.6, lng=104.1)],
        steps=[RouteStep(instruction="向东步行", distance_m=1200, duration_s=900)],
    )

    assert route.mode == "walking"
    assert len(route.polyline) == 2


def test_poi_and_weather_are_structured():
    poi = Poi(
        id="B001",
        name="武侯祠",
        address="武侯祠大街231号",
        category="风景名胜",
        location=GeoPoint(lat=30.645, lng=104.043),
    )
    weather = WeatherForecast(
        city="成都",
        date=date(2026, 8, 1),
        day_weather="多云",
        night_weather="阵雨",
        day_temp_c=30,
        night_temp_c=23,
    )

    assert poi.location.lng == 104.043
    assert weather.date.isoformat() == "2026-08-01"
