"""Trip aggregate models and invariants."""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TripStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class ActivityStatus(str, Enum):
    PLANNED = "planned"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address: str = ""


class DataSource(BaseModel):
    provider: str
    fetched_at: datetime
    confidence: float = Field(default=1.0, ge=0, le=1)
    stale: bool = False
    estimated: bool = False
    warnings: list[str] = Field(default_factory=list)


class Activity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    starts_at: datetime
    ends_at: datetime
    cost: float = Field(default=0, ge=0)
    location: Location
    locked: bool = False
    status: ActivityStatus = ActivityStatus.PLANNED
    source: Optional[DataSource] = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class WeatherSummary(BaseModel):
    day_weather: str
    night_weather: str = ""
    day_temp_c: Optional[float] = None
    night_temp_c: Optional[float] = None
    source: DataSource


class TransportLeg(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    from_activity_id: str
    to_activity_id: str
    mode: Literal["walking", "driving"]
    distance_m: int = Field(ge=0)
    duration_s: int = Field(ge=0)
    polyline: list[Location] = Field(default_factory=list)
    source: DataSource


class TripDay(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    date: date
    activities: list[Activity] = Field(default_factory=list)
    weather: Optional[WeatherSummary] = None
    transport_legs: list[TransportLeg] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_schedule(self):
        self.activities.sort(key=lambda item: item.starts_at)
        for item in self.activities:
            if item.starts_at.date() != self.date or item.ends_at.date() != self.date:
                raise ValueError("activity outside trip day")
        for previous, current in zip(self.activities, self.activities[1:]):
            if current.starts_at < previous.ends_at:
                raise ValueError("activities overlap")
        activity_ids = {item.id for item in self.activities}
        for leg in self.transport_legs:
            if leg.from_activity_id not in activity_ids or leg.to_activity_id not in activity_ids:
                raise ValueError("transport leg references unknown activity")
        return self


class TripDraft(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    destination: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    party_size: int = Field(default=1, ge=1, le=50)
    budget_limit: float = Field(default=0, ge=0)
    status: TripStatus = TripStatus.PLANNING
    days: list[TripDay] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates_and_ids(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        if len({day.id for day in self.days}) != len(self.days):
            raise ValueError("duplicate day id")

        activities = [item for day in self.days for item in day.activities]
        if len({item.id for item in activities}) != len(activities):
            raise ValueError("duplicate activity id")

        for day in self.days:
            if not self.start_date <= day.date <= self.end_date:
                raise ValueError("day outside trip dates")
        return self


class Trip(TripDraft):
    id: str
    user_id: str
    conversation_id: Optional[str] = None
    current_revision: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class TripRevisionSummary(BaseModel):
    revision: int
    base_revision: int
    reason: str
    created_at: datetime
