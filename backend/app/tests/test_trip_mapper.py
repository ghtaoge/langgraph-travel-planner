"""Mapping enriched PlanningGraph state into the durable Trip aggregate."""

from datetime import date

from app.modules.planner.trip_mapper import build_trip_draft
from app.modules.trips.models import TripStatus


def source():
    return {
        "provider": "amap",
        "fetched_at": "2026-07-22T00:00:00Z",
        "confidence": 1,
        "stale": False,
        "estimated": False,
        "warnings": [],
    }


def test_mapper_preserves_enriched_weather_routes_and_sources():
    state = {
        "thread_id": "thread-1",
        "destination": "成都",
        "duration": 1,
        "start_date": date(2026, 8, 1),
        "selected_plan": {"title": "成都文化一日游"},
        "budget": {"total_budget": 1200},
        "itinerary": {
            "daily_plans": [{
                "day": 1,
                "date": "2026-08-01",
                "activities": [
                    {
                        "id": "a1",
                        "name": "武侯祠",
                        "description": "三国文化",
                        "time": "09:00-11:00",
                        "cost": 50,
                        "location": {"lat": 30.64, "lng": 104.04, "address": "武侯区"},
                        "source": source(),
                    },
                    {
                        "id": "a2",
                        "name": "杜甫草堂",
                        "description": "诗歌文化",
                        "time": "13:00-15:00",
                        "cost": 50,
                        "location": {"lat": 30.66, "lng": 104.03, "address": "青羊区"},
                        "source": source(),
                    },
                ],
                "weather": {
                    "day_weather": "多云",
                    "night_weather": "阵雨",
                    "day_temp_c": 30,
                    "night_temp_c": 23,
                    "source": source(),
                },
                "route_legs": [{
                    "from_activity_id": "a1",
                    "to_activity_id": "a2",
                    "mode": "walking",
                    "distance_m": 1200,
                    "duration_s": 900,
                    "polyline": [
                        {"lat": 30.64, "lng": 104.04},
                        {"lat": 30.66, "lng": 104.03},
                    ],
                    "source": source(),
                }],
            }],
        },
    }

    draft = build_trip_draft(state)

    assert draft.status is TripStatus.ACTIVE
    assert draft.start_date == date(2026, 8, 1)
    assert draft.days[0].activities[0].source.provider == "amap"
    assert draft.days[0].weather.day_weather == "多云"
    assert draft.days[0].transport_legs[0].distance_m == 1200
    assert draft.budget_limit == 1200


def test_mapper_assigns_non_overlapping_times_when_llm_time_is_missing():
    state = {
        "thread_id": "thread-1",
        "destination": "成都",
        "duration": 1,
        "start_date": "2026-08-01",
        "selected_plan": {"title": "成都一日游"},
        "itinerary": {"daily_plans": [{
            "day": 1,
            "activities": [
                {"id": "a1", "name": "A", "location": {"lat": 30, "lng": 104}},
                {"id": "a2", "name": "B", "location": {"lat": 30.1, "lng": 104.1}},
            ],
        }]},
    }

    draft = build_trip_draft(state)

    first, second = draft.days[0].activities
    assert first.ends_at <= second.starts_at
