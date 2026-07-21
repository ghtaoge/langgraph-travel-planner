"""Trip aggregate model tests."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.modules.trips.models import (
    Activity,
    ActivityStatus,
    DataSource,
    Location,
    TransportLeg,
    TripDay,
    TripDraft,
    WeatherSummary,
)


def activity(name: str, start: int, end: int) -> Activity:
    return Activity(
        id=name.lower(),
        name=name,
        description="",
        starts_at=datetime(2026, 8, 1, start),
        ends_at=datetime(2026, 8, 1, end),
        cost=50,
        location=Location(lat=30.57, lng=104.06, address="成都"),
    )


def test_trip_day_sorts_activities_by_start_time():
    day = TripDay(
        id="day-1",
        date=date(2026, 8, 1),
        activities=[activity("B", 13, 14), activity("A", 9, 10)],
    )

    assert [item.name for item in day.activities] == ["A", "B"]


def test_trip_day_rejects_overlapping_activities():
    with pytest.raises(ValidationError, match="overlap"):
        TripDay(
            id="day-1",
            date=date(2026, 8, 1),
            activities=[activity("A", 9, 11), activity("B", 10, 12)],
        )


def test_activity_rejects_reverse_time_range():
    with pytest.raises(ValidationError, match="ends_at"):
        activity("A", 11, 9)


def test_trip_draft_rejects_day_outside_trip_dates():
    with pytest.raises(ValidationError, match="outside trip dates"):
        TripDraft(
            title="成都周末",
            destination="成都",
            start_date=date(2026, 8, 2),
            end_date=date(2026, 8, 3),
            party_size=2,
            budget_limit=3000,
            days=[TripDay(id="day-1", date=date(2026, 8, 1), activities=[])],
        )


def test_trip_draft_rejects_duplicate_activity_ids():
    with pytest.raises(ValidationError, match="duplicate activity id"):
        TripDraft(
            title="成都周末",
            destination="成都",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 2),
            days=[
                TripDay(id="day-1", date=date(2026, 8, 1), activities=[activity("A", 9, 10)]),
                TripDay(id="day-2", date=date(2026, 8, 2), activities=[
                    Activity(
                        **activity("B", 11, 12).model_dump(exclude={"id", "starts_at", "ends_at"}),
                        id="a",
                        starts_at=datetime(2026, 8, 2, 11),
                        ends_at=datetime(2026, 8, 2, 12),
                    )
                ]),
            ],
        )


def test_activity_defaults_to_planned_and_unlocked():
    item = activity("A", 9, 10)

    assert item.status is ActivityStatus.PLANNED
    assert item.locked is False


def test_trip_day_keeps_weather_routes_and_source_metadata():
    source = DataSource(
        provider="amap",
        fetched_at=datetime(2026, 7, 22),
        confidence=1,
    )
    day = TripDay(
        id="day-1",
        date=date(2026, 8, 1),
        activities=[activity("A", 9, 10), activity("B", 11, 12)],
        weather=WeatherSummary(
            day_weather="多云",
            night_weather="阵雨",
            day_temp_c=30,
            night_temp_c=23,
            source=source,
        ),
        transport_legs=[
            TransportLeg(
                from_activity_id="a",
                to_activity_id="b",
                mode="walking",
                distance_m=1200,
                duration_s=900,
                polyline=[
                    Location(lat=30.57, lng=104.06),
                    Location(lat=30.58, lng=104.07),
                ],
                source=source,
            )
        ],
    )

    assert day.weather.source.provider == "amap"
    assert day.transport_legs[0].duration_s == 900
