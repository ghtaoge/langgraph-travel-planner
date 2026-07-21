"""Typed, side-effect-free patch operations for Trip snapshots."""

from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.modules.trips.errors import (
    PatchValidationError,
    ProtectedActivityError,
    RevisionConflictError,
)
from app.modules.trips.models import Activity, ActivityStatus, Location, Trip, TripDay


class ActivityChanges(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    cost: Optional[float] = Field(default=None, ge=0)
    location: Optional[Location] = None


class AddActivity(BaseModel):
    op: Literal["add_activity"] = "add_activity"
    day_id: str
    activity: Activity
    after_activity_id: Optional[str] = None


class UpdateActivity(BaseModel):
    op: Literal["update_activity"] = "update_activity"
    activity_id: str
    changes: ActivityChanges


class RemoveActivity(BaseModel):
    op: Literal["remove_activity"] = "remove_activity"
    activity_id: str


class MoveActivity(BaseModel):
    op: Literal["move_activity"] = "move_activity"
    activity_id: str
    target_day_id: str
    starts_at: datetime
    ends_at: datetime
    after_activity_id: Optional[str] = None


PatchOperation = Annotated[
    Union[AddActivity, UpdateActivity, RemoveActivity, MoveActivity],
    Field(discriminator="op"),
]


class TripPatch(BaseModel):
    base_revision: int = Field(ge=1)
    scope: Literal["activity", "day", "remaining"]
    reason: str = Field(min_length=1, max_length=500)
    operations: list[PatchOperation] = Field(min_length=1)


def _find_day(trip: Trip, day_id: str) -> TripDay:
    for day in trip.days:
        if day.id == day_id:
            return day
    raise PatchValidationError(f"day not found: {day_id}")


def _find_activity(trip: Trip, activity_id: str) -> tuple[TripDay, int, Activity]:
    for day in trip.days:
        for index, activity in enumerate(day.activities):
            if activity.id == activity_id:
                return day, index, activity
    raise PatchValidationError(f"activity not found: {activity_id}")


def _ensure_mutable(activity: Activity) -> None:
    if activity.locked or activity.status is not ActivityStatus.PLANNED:
        raise ProtectedActivityError(f"activity is protected: {activity.id}")


def _insert(day: TripDay, activity: Activity, after_activity_id: Optional[str]) -> None:
    if after_activity_id is None:
        day.activities.append(activity)
        return

    for index, existing in enumerate(day.activities):
        if existing.id == after_activity_id:
            day.activities.insert(index + 1, activity)
            return
    raise PatchValidationError(f"anchor activity not found: {after_activity_id}")


def _ensure_new_activity(trip: Trip, activity: Activity) -> None:
    if activity.locked or activity.status is not ActivityStatus.PLANNED:
        raise PatchValidationError("new activity must be planned and unlocked")
    try:
        _find_activity(trip, activity.id)
    except PatchValidationError:
        return
    raise PatchValidationError(f"duplicate activity id: {activity.id}")


def apply_trip_patch(trip: Trip, patch: TripPatch) -> Trip:
    """Apply all operations atomically to a deep copy and revalidate the aggregate."""
    if patch.base_revision != trip.current_revision:
        raise RevisionConflictError(
            f"expected revision {trip.current_revision}, got {patch.base_revision}"
        )

    changed = trip.model_copy(deep=True)
    for operation in patch.operations:
        if isinstance(operation, AddActivity):
            _ensure_new_activity(changed, operation.activity)
            target_day = _find_day(changed, operation.day_id)
            _insert(target_day, operation.activity.model_copy(deep=True), operation.after_activity_id)
            continue

        if isinstance(operation, UpdateActivity):
            day, index, activity = _find_activity(changed, operation.activity_id)
            _ensure_mutable(activity)
            values = operation.changes.model_dump(exclude_none=True)
            day.activities[index] = Activity.model_validate(
                activity.model_copy(update=values).model_dump(mode="python")
            )
            continue

        if isinstance(operation, RemoveActivity):
            day, index, activity = _find_activity(changed, operation.activity_id)
            _ensure_mutable(activity)
            day.activities.pop(index)
            continue

        source_day, index, activity = _find_activity(changed, operation.activity_id)
        _ensure_mutable(activity)
        source_day.activities.pop(index)
        moved = Activity.model_validate(
            activity.model_copy(
                update={"starts_at": operation.starts_at, "ends_at": operation.ends_at}
            ).model_dump(mode="python")
        )
        target_day = _find_day(changed, operation.target_day_id)
        _insert(target_day, moved, operation.after_activity_id)

    return Trip.model_validate(changed.model_dump(mode="python"))
