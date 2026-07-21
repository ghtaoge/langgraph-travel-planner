"""Typed Trip patch behavior and protection tests."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.modules.trips.errors import (
    PatchValidationError,
    ProtectedActivityError,
    RevisionConflictError,
)
from app.modules.trips.models import Activity, ActivityStatus, Location, Trip, TripDay
from app.modules.trips.patches import (
    ActivityChanges,
    AddActivity,
    MoveActivity,
    RemoveActivity,
    TripPatch,
    UpdateActivity,
    apply_trip_patch,
)


def make_activity(
    activity_id: str,
    day: int,
    start: int,
    end: int,
    *,
    locked: bool = False,
    status: ActivityStatus = ActivityStatus.PLANNED,
) -> Activity:
    return Activity(
        id=activity_id,
        name=activity_id,
        starts_at=datetime(2026, 8, day, start),
        ends_at=datetime(2026, 8, day, end),
        location=Location(lat=30.64, lng=104.04, address="成都"),
        locked=locked,
        status=status,
    )


def trip(*, locked: bool = False, status: ActivityStatus = ActivityStatus.PLANNED) -> Trip:
    return Trip(
        id="trip-1",
        user_id="user-1",
        title="成都三日游",
        destination="成都",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
        days=[
            TripDay(
                id="day-1",
                date=date(2026, 8, 1),
                activities=[make_activity("a1", 1, 9, 11, locked=locked, status=status)],
            ),
            TripDay(id="day-2", date=date(2026, 8, 2), activities=[]),
        ],
    )


def test_patch_updates_mutable_activity_without_mutating_original():
    original = trip()
    patch = TripPatch(
        base_revision=1,
        scope="activity",
        reason="减少停留时间",
        operations=[
            UpdateActivity(
                activity_id="a1",
                changes=ActivityChanges(ends_at=datetime(2026, 8, 1, 10, 30)),
            )
        ],
    )

    changed = apply_trip_patch(original, patch)

    assert original.days[0].activities[0].ends_at.hour == 11
    assert changed.days[0].activities[0].ends_at.minute == 30


@pytest.mark.parametrize(
    ("locked", "status"),
    [
        (True, ActivityStatus.PLANNED),
        (False, ActivityStatus.COMPLETED),
        (False, ActivityStatus.SKIPPED),
    ],
)
def test_patch_cannot_remove_protected_activity(locked, status):
    patch = TripPatch(
        base_revision=1,
        scope="activity",
        reason="替换景点",
        operations=[RemoveActivity(activity_id="a1")],
    )

    with pytest.raises(ProtectedActivityError):
        apply_trip_patch(trip(locked=locked, status=status), patch)


def test_patch_rejects_stale_base_revision():
    patch = TripPatch(
        base_revision=2,
        scope="activity",
        reason="修改",
        operations=[RemoveActivity(activity_id="a1")],
    )

    with pytest.raises(RevisionConflictError):
        apply_trip_patch(trip(), patch)


def test_move_across_days_uses_target_day_times():
    patch = TripPatch(
        base_revision=1,
        scope="day",
        reason="雨天调整",
        operations=[
            MoveActivity(
                activity_id="a1",
                target_day_id="day-2",
                starts_at=datetime(2026, 8, 2, 14),
                ends_at=datetime(2026, 8, 2, 16),
            )
        ],
    )

    changed = apply_trip_patch(trip(), patch)

    assert changed.days[0].activities == []
    assert changed.days[1].activities[0].id == "a1"


def test_add_activity_rejects_duplicate_id():
    patch = TripPatch(
        base_revision=1,
        scope="day",
        reason="增加景点",
        operations=[AddActivity(day_id="day-1", activity=make_activity("a1", 1, 13, 14))],
    )

    with pytest.raises(PatchValidationError, match="duplicate activity id"):
        apply_trip_patch(trip(), patch)


def test_patch_revalidates_schedule_after_update():
    source = trip()
    source.days[0] = TripDay(
        id="day-1",
        date=date(2026, 8, 1),
        activities=[make_activity("a1", 1, 9, 11), make_activity("a2", 1, 12, 13)],
    )
    patch = TripPatch(
        base_revision=1,
        scope="activity",
        reason="延长游览",
        operations=[
            UpdateActivity(
                activity_id="a1",
                changes=ActivityChanges(ends_at=datetime(2026, 8, 1, 12, 30)),
            )
        ],
    )

    with pytest.raises(ValidationError, match="overlap"):
        apply_trip_patch(source, patch)
