"""Convert enriched PlanningGraph state into a durable TripDraft."""

import re
from datetime import date, datetime, time, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from app.modules.trips.models import (
    Activity,
    DataSource,
    Location,
    TransportLeg,
    TripDay,
    TripDraft,
    TripStatus,
    WeatherSummary,
)

TIME_RANGE = re.compile(
    r"(?P<start_hour>\d{1,2}):(?P<start_minute>\d{2})\s*[-–—]\s*"
    r"(?P<end_hour>\d{1,2}):(?P<end_minute>\d{2})"
)


def _date(value, fallback: date) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return fallback


def _source(value, label: str) -> DataSource:
    if isinstance(value, dict):
        return DataSource.model_validate(value)
    return DataSource(
        provider="unknown",
        fetched_at=datetime.now(timezone.utc),
        confidence=0.3,
        estimated=True,
        warnings=[f"{label}缺少数据来源"],
    )


def _activity_times(raw: dict, day_date: date, index: int) -> tuple[datetime, datetime]:
    match = TIME_RANGE.search(str(raw.get("time") or ""))
    if match:
        starts_at = datetime.combine(
            day_date,
            time(int(match["start_hour"]), int(match["start_minute"])),
        )
        ends_at = datetime.combine(
            day_date,
            time(int(match["end_hour"]), int(match["end_minute"])),
        )
        if ends_at > starts_at:
            return starts_at, ends_at

    starts_at = datetime.combine(day_date, time(8)) + timedelta(minutes=90 * index)
    duration_minutes = max(30, round(float(raw.get("duration_hours") or 1) * 60))
    return starts_at, starts_at + timedelta(minutes=duration_minutes)


def _location(value, activity_name: str) -> Location:
    if not isinstance(value, dict) or "lat" not in value or "lng" not in value:
        raise ValueError(f"activity has not been geocoded: {activity_name}")
    return Location.model_validate(value)


def build_trip_draft(state: dict) -> TripDraft:
    intent = state.get("intent") or {}
    start_date = _date(state.get("start_date") or intent.get("start_date"), date.today())
    duration = max(1, int(state.get("duration") or intent.get("duration") or 1))
    thread_id = state.get("thread_id", "trip")
    days = []

    for day_index, raw_day in enumerate((state.get("itinerary") or {}).get("daily_plans") or []):
        day_date = _date(raw_day.get("date"), start_date + timedelta(days=day_index))
        activities = []
        for activity_index, raw_activity in enumerate(raw_day.get("activities") or []):
            name = str(raw_activity.get("name") or f"活动{activity_index + 1}")
            starts_at, ends_at = _activity_times(raw_activity, day_date, activity_index)
            activity_id = raw_activity.get("id") or str(
                uuid5(NAMESPACE_URL, f"{thread_id}:{day_index}:{activity_index}:{name}")
            )
            activities.append(
                Activity(
                    id=activity_id,
                    name=name,
                    description=str(raw_activity.get("description") or ""),
                    starts_at=starts_at,
                    ends_at=ends_at,
                    cost=max(0, float(raw_activity.get("cost") or 0)),
                    location=_location(raw_activity.get("location"), name),
                    source=_source(raw_activity.get("source"), f"{name}位置"),
                )
            )

        weather = None
        raw_weather = raw_day.get("weather")
        if isinstance(raw_weather, dict):
            weather = WeatherSummary(
                day_weather=str(raw_weather.get("day_weather") or ""),
                night_weather=str(raw_weather.get("night_weather") or ""),
                day_temp_c=raw_weather.get("day_temp_c"),
                night_temp_c=raw_weather.get("night_temp_c"),
                source=_source(raw_weather.get("source"), f"{day_date}天气"),
            )

        transport_legs = []
        for raw_leg in raw_day.get("route_legs") or []:
            transport_legs.append(
                TransportLeg(
                    id=raw_leg.get("id") or str(uuid5(
                        NAMESPACE_URL,
                        f"{thread_id}:{raw_leg.get('from_activity_id')}:{raw_leg.get('to_activity_id')}",
                    )),
                    from_activity_id=raw_leg["from_activity_id"],
                    to_activity_id=raw_leg["to_activity_id"],
                    mode=raw_leg.get("mode", "walking"),
                    distance_m=int(raw_leg.get("distance_m") or 0),
                    duration_s=int(raw_leg.get("duration_s") or 0),
                    polyline=[Location.model_validate(point) for point in raw_leg.get("polyline") or []],
                    source=_source(raw_leg.get("source"), "路线"),
                )
            )

        days.append(
            TripDay(
                id=raw_day.get("id") or str(uuid5(NAMESPACE_URL, f"{thread_id}:day:{day_index}")),
                date=day_date,
                activities=activities,
                weather=weather,
                transport_legs=transport_legs,
            )
        )

    budget = state.get("budget") or {}
    selected_plan = state.get("selected_plan") or {}
    return TripDraft(
        title=selected_plan.get("title") or f"{state.get('destination', '旅行')}{duration}日游",
        destination=state.get("destination") or intent.get("destination") or "",
        start_date=start_date,
        end_date=start_date + timedelta(days=duration - 1),
        party_size=max(1, int(state.get("party_size") or intent.get("party_size") or 1)),
        budget_limit=max(0, float(budget.get("total_budget") or intent.get("budget_limit") or 0)),
        status=TripStatus.ACTIVE,
        days=days,
    )
