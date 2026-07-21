"""Provider-neutral travel data models."""

from datetime import date, datetime
from typing import Generic, Literal, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ProviderMeta(BaseModel):
    provider: str
    fetched_at: datetime
    confidence: float = Field(default=1.0, ge=0, le=1)
    stale: bool = False
    estimated: bool = False
    warnings: list[str] = Field(default_factory=list)


class ProviderResult(BaseModel, Generic[T]):
    data: T
    meta: ProviderMeta


class GeoPoint(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    address: str = ""
    adcode: str = ""


class Poi(BaseModel):
    id: str
    name: str
    address: str = ""
    category: str = ""
    location: GeoPoint
    distance_m: Optional[int] = Field(default=None, ge=0)


class WeatherForecast(BaseModel):
    city: str
    date: date
    day_weather: str
    night_weather: str = ""
    day_temp_c: Optional[float] = None
    night_temp_c: Optional[float] = None
    day_wind: str = ""
    night_wind: str = ""


class RouteStep(BaseModel):
    instruction: str
    distance_m: int = Field(ge=0)
    duration_s: int = Field(ge=0)


class RoutePlan(BaseModel):
    mode: Literal["walking", "driving"]
    distance_m: int = Field(ge=0)
    duration_s: int = Field(ge=0)
    polyline: list[GeoPoint] = Field(default_factory=list)
    steps: list[RouteStep] = Field(default_factory=list)


class CacheEntry(BaseModel):
    key: str
    data_type: str
    payload: dict
    fetched_at: datetime
    expires_at: datetime

    def is_stale(self, now: datetime) -> bool:
        return self.expires_at <= now
