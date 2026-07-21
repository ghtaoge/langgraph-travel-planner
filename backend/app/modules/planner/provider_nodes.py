"""Planning nodes that research and enrich itinerary data through providers."""

import asyncio
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from app.modules.providers.factory import get_travel_data_service
from app.modules.providers.models import GeoPoint, ProviderMeta


def _trip_start_date(state: dict) -> date:
    value = state.get("start_date") or (state.get("intent") or {}).get("start_date")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return date.today()


def _day_date(raw_value, start_date: date, day_index: int) -> date:
    if isinstance(raw_value, date):
        return raw_value
    if isinstance(raw_value, str):
        try:
            return date.fromisoformat(raw_value)
        except ValueError:
            pass
    return start_date + timedelta(days=day_index)


def _collect_warnings(meta: ProviderMeta, label: str) -> list[str]:
    warnings = list(meta.warnings)
    if meta.estimated:
        warnings.append(f"{label}使用估算数据")
    if meta.stale:
        warnings.append(f"{label}数据已过期")
    return warnings


async def provider_research_node(state: dict) -> dict:
    destination = state.get("destination", "成都")
    style = state.get("travel_style", "文化游").removesuffix("游") or "景点"
    result = await get_travel_data_service().search_pois(destination, style, limit=10)
    return {
        "research_result": {
            "_provider": {
                "pois": [item.model_dump(mode="json") for item in result.data],
                "meta": result.meta.model_dump(mode="json"),
            }
        },
        "provider_warnings": _collect_warnings(result.meta, "POI"),
    }


async def _enrich_activity(
    service,
    activity: dict,
    *,
    destination: str,
    thread_id: str,
    day_index: int,
    activity_index: int,
):
    item = deepcopy(activity)
    item["id"] = item.get("id") or str(
        uuid5(
            NAMESPACE_URL,
            f"{thread_id}:{day_index}:{activity_index}:{item.get('name', '')}",
        )
    )
    raw_location = item.get("location")
    if isinstance(raw_location, dict) and "lat" in raw_location and "lng" in raw_location:
        point = GeoPoint.model_validate(raw_location)
        meta = ProviderMeta(
            provider="existing",
            fetched_at=datetime.now(timezone.utc),
            confidence=1,
        )
    else:
        address = str(raw_location or item.get("name") or destination)
        geocode = await service.geocode(address, destination)
        point = geocode.data
        meta = geocode.meta
    item["location"] = point.model_dump(mode="json")
    item["source"] = meta.model_dump(mode="json")
    return item, _collect_warnings(meta, f"{item.get('name', '活动')}位置")


async def _enrich_day(service, state: dict, day_plan: dict, day_index: int):
    destination = state.get("destination", "成都")
    thread_id = state.get("thread_id", "trip")
    target_date = _day_date(day_plan.get("date"), _trip_start_date(state), day_index)
    day = deepcopy(day_plan)
    day["date"] = target_date.isoformat()

    activity_results = await asyncio.gather(*[
        _enrich_activity(
            service,
            activity,
            destination=destination,
            thread_id=thread_id,
            day_index=day_index,
            activity_index=index,
        )
        for index, activity in enumerate(day.get("activities") or [])
    ])
    activities = [result[0] for result in activity_results]
    warnings = [warning for result in activity_results for warning in result[1]]
    day["activities"] = activities

    weather = await service.weather(destination, target_date)
    day["weather"] = {
        **weather.data.model_dump(mode="json"),
        "source": weather.meta.model_dump(mode="json"),
    }
    warnings.extend(_collect_warnings(weather.meta, f"{target_date}天气"))

    route_results = await asyncio.gather(*[
        service.route(
            GeoPoint.model_validate(current["location"]),
            GeoPoint.model_validate(following["location"]),
            mode="walking",
        )
        for current, following in zip(activities, activities[1:])
    ])
    day["route_legs"] = []
    for index, route in enumerate(route_results):
        day["route_legs"].append({
            "from_activity_id": activities[index]["id"],
            "to_activity_id": activities[index + 1]["id"],
            **route.data.model_dump(mode="json"),
            "source": route.meta.model_dump(mode="json"),
        })
        warnings.extend(_collect_warnings(route.meta, "路线"))
    return day, warnings


async def enrich_itinerary_node(state: dict) -> dict:
    itinerary = deepcopy(state.get("itinerary") or {})
    service = get_travel_data_service()
    day_results = await asyncio.gather(*[
        _enrich_day(service, state, day_plan, index)
        for index, day_plan in enumerate(itinerary.get("daily_plans") or [])
    ])
    itinerary["daily_plans"] = [result[0] for result in day_results]
    warnings = list(state.get("provider_warnings") or [])
    warnings.extend(warning for result in day_results for warning in result[1])
    if not (state.get("start_date") or (state.get("intent") or {}).get("start_date")):
        warnings.append("未提供出发日期，天气查询与行程日期暂按当前日期计算")
    return {
        "itinerary": itinerary,
        "provider_warnings": list(dict.fromkeys(warnings)),
    }
