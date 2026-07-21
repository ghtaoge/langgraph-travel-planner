# Trip Domain and Revisions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a durable `Trip` aggregate, protected patch engine, PostgreSQL revision history, and authenticated Trip API without changing the existing planning graph.

**Architecture:** PostgreSQL stores the current Trip snapshot and an immutable snapshot for every revision. Pure domain code validates trip invariants and applies typed patch operations; an async repository owns atomic optimistic-lock transactions, while FastAPI routes provide authenticated CRUD and revision endpoints.

**Tech Stack:** Python 3.11, Pydantic 2, FastAPI, asyncpg, PostgreSQL 16, pytest, pytest-asyncio

---

## Delivery Roadmap

The approved design spans several independently testable subsystems. Implement them as separate plans so each phase lands working software and later plans can use the code that actually exists:

1. **This plan:** Trip domain, patch protection, PostgreSQL revisions, restore, and authenticated APIs.
2. Provider contracts, PostgreSQL cache, Amap geocoding/POI/routes/weather, and explicit degradation metadata.
3. `PlanningGraph` refactor that persists the first confirmed Trip revision.
4. Vue Trip workspace with timeline, map linkage, structured editing, and responsive tabs.
5. `TripOperationGraph`, generated patch validation, visual diff, and user-confirmed application.
6. Travel mode, actual-expense ledger, event suggestions, evaluation dataset, and end-to-end observability.

Do not add Provider, LangGraph, or frontend behavior in this phase. The usable outcome is an authenticated API through which a client can create a Trip, safely change it with a typed patch, inspect its revision history, and restore an older snapshot.

## File Map

| File | Responsibility |
|---|---|
| `backend/app/modules/trips/models.py` | Trip aggregate, activity status, day/time invariants, revision summary |
| `backend/app/modules/trips/errors.py` | Domain and persistence exceptions mapped by the API |
| `backend/app/modules/trips/patches.py` | Typed operations and pure `apply_trip_patch` function |
| `backend/app/modules/trips/repository.py` | Snapshot serialization and atomic PostgreSQL revision transactions |
| `backend/app/api/schemas/trip.py` | HTTP request schemas separate from persisted models |
| `backend/app/api/routes/trips.py` | Authenticated Trip CRUD, patch, history, and restore endpoints |
| `backend/app/migrations/init.sql` | `trips` and `trip_revisions` tables and indexes |
| `backend/app/main.py` | Register the Trip router |
| `backend/app/tests/test_trip_models.py` | Aggregate invariant tests |
| `backend/app/tests/test_trip_patches.py` | Patch behavior and protected-item tests |
| `backend/app/tests/test_trip_schema.py` | Migration contract test |
| `backend/app/tests/test_trip_repository.py` | PostgreSQL transaction and optimistic-lock integration tests |
| `backend/app/tests/test_trips_api.py` | Route contract and error mapping tests |

### Task 1: Define the Trip Aggregate

**Files:**
- Create: `backend/app/modules/trips/__init__.py`
- Create: `backend/app/modules/trips/models.py`
- Test: `backend/app/tests/test_trip_models.py`

- [ ] **Step 1: Write failing aggregate invariant tests**

Create `backend/app/tests/test_trip_models.py`:

```python
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.modules.trips.models import Activity, ActivityStatus, Location, TripDay, TripDraft


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


def test_activity_defaults_to_planned_and_unlocked():
    item = activity("A", 9, 10)
    assert item.status is ActivityStatus.PLANNED
    assert item.locked is False
```

- [ ] **Step 2: Run the tests and verify the import failure**

Run from `backend`:

```powershell
pytest app/tests/test_trip_models.py -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'app.modules.trips'`.

- [ ] **Step 3: Implement focused Pydantic domain models**

Create an empty `backend/app/modules/trips/__init__.py`, then create `backend/app/modules/trips/models.py`:

```python
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
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


class TripDay(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    date: date
    activities: list[Activity] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_schedule(self):
        self.activities.sort(key=lambda item: item.starts_at)
        for item in self.activities:
            if item.starts_at.date() != self.date or item.ends_at.date() != self.date:
                raise ValueError("activity outside trip day")
        for previous, current in zip(self.activities, self.activities[1:]):
            if current.starts_at < previous.ends_at:
                raise ValueError("activities overlap")
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
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        if len({day.id for day in self.days}) != len(self.days):
            raise ValueError("duplicate day id")
        if len({item.id for day in self.days for item in day.activities}) != sum(
            len(day.activities) for day in self.days
        ):
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
```

- [ ] **Step 4: Run the aggregate tests**

Run:

```powershell
pytest app/tests/test_trip_models.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit the aggregate**

```powershell
git add backend/app/modules/trips backend/app/tests/test_trip_models.py
git commit -m "feat: add trip domain aggregate"
```

### Task 2: Implement Protected Trip Patches

**Files:**
- Create: `backend/app/modules/trips/errors.py`
- Create: `backend/app/modules/trips/patches.py`
- Test: `backend/app/tests/test_trip_patches.py`

- [ ] **Step 1: Write failing patch behavior tests**

Create `backend/app/tests/test_trip_patches.py`:

```python
from datetime import date, datetime

import pytest

from app.modules.trips.errors import ProtectedActivityError, RevisionConflictError
from app.modules.trips.models import Activity, ActivityStatus, Location, Trip, TripDay
from app.modules.trips.patches import (
    ActivityChanges,
    MoveActivity,
    RemoveActivity,
    TripPatch,
    UpdateActivity,
    apply_trip_patch,
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
                activities=[Activity(
                    id="a1",
                    name="武侯祠",
                    starts_at=datetime(2026, 8, 1, 9),
                    ends_at=datetime(2026, 8, 1, 11),
                    location=Location(lat=30.64, lng=104.04, address="武侯区"),
                    locked=locked,
                    status=status,
                )],
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
        operations=[UpdateActivity(
            activity_id="a1",
            changes=ActivityChanges(ends_at=datetime(2026, 8, 1, 10, 30)),
        )],
    )
    changed = apply_trip_patch(original, patch)
    assert original.days[0].activities[0].ends_at.hour == 11
    assert changed.days[0].activities[0].ends_at.minute == 30


@pytest.mark.parametrize(
    ("locked", "status"),
    [(True, ActivityStatus.PLANNED), (False, ActivityStatus.COMPLETED)],
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


def test_move_across_days_requires_target_day_times():
    patch = TripPatch(
        base_revision=1,
        scope="day",
        reason="雨天调整",
        operations=[MoveActivity(
            activity_id="a1",
            target_day_id="day-2",
            starts_at=datetime(2026, 8, 2, 14),
            ends_at=datetime(2026, 8, 2, 16),
        )],
    )
    changed = apply_trip_patch(trip(), patch)
    assert changed.days[0].activities == []
    assert changed.days[1].activities[0].id == "a1"
```

- [ ] **Step 2: Run the tests and verify missing patch types**

Run:

```powershell
pytest app/tests/test_trip_patches.py -q
```

Expected: collection fails because `app.modules.trips.patches` does not exist.

- [ ] **Step 3: Add explicit domain errors**

Create `backend/app/modules/trips/errors.py`:

```python
class TripError(Exception):
    """Base error for Trip operations."""


class TripNotFoundError(TripError):
    pass


class RevisionNotFoundError(TripError):
    pass


class RevisionConflictError(TripError):
    pass


class PatchValidationError(TripError):
    pass


class ProtectedActivityError(PatchValidationError):
    pass
```

- [ ] **Step 4: Implement typed operations and the pure patch function**

Create `backend/app/modules/trips/patches.py`:

```python
from datetime import datetime
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

from app.modules.trips.errors import (
    PatchValidationError,
    ProtectedActivityError,
    RevisionConflictError,
)
from app.modules.trips.models import Activity, ActivityStatus, Location, Trip


class ActivityChanges(BaseModel):
    name: Optional[str] = None
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


def _find_day(trip: Trip, day_id: str):
    for day in trip.days:
        if day.id == day_id:
            return day
    raise PatchValidationError(f"day not found: {day_id}")


def _find_activity(trip: Trip, activity_id: str):
    for day in trip.days:
        for index, activity in enumerate(day.activities):
            if activity.id == activity_id:
                return day, index, activity
    raise PatchValidationError(f"activity not found: {activity_id}")


def _ensure_mutable(activity: Activity):
    if activity.locked or activity.status is not ActivityStatus.PLANNED:
        raise ProtectedActivityError(f"activity is protected: {activity.id}")


def _insert(day, activity: Activity, after_activity_id: Optional[str]):
    if after_activity_id is None:
        day.activities.append(activity)
        return
    for index, existing in enumerate(day.activities):
        if existing.id == after_activity_id:
            day.activities.insert(index + 1, activity)
            return
    raise PatchValidationError(f"anchor activity not found: {after_activity_id}")


def apply_trip_patch(trip: Trip, patch: TripPatch) -> Trip:
    if patch.base_revision != trip.current_revision:
        raise RevisionConflictError(
            f"expected revision {trip.current_revision}, got {patch.base_revision}"
        )

    changed = trip.model_copy(deep=True)
    for operation in patch.operations:
        if isinstance(operation, AddActivity):
            if operation.activity.locked or operation.activity.status is not ActivityStatus.PLANNED:
                raise PatchValidationError("new activity must be planned and unlocked")
            try:
                _find_activity(changed, operation.activity.id)
            except PatchValidationError:
                pass
            else:
                raise PatchValidationError(f"duplicate activity id: {operation.activity.id}")
            _insert(_find_day(changed, operation.day_id), operation.activity, operation.after_activity_id)

        elif isinstance(operation, UpdateActivity):
            day, index, activity = _find_activity(changed, operation.activity_id)
            _ensure_mutable(activity)
            values = operation.changes.model_dump(exclude_none=True)
            day.activities[index] = Activity.model_validate(
                activity.model_copy(update=values).model_dump(mode="python")
            )

        elif isinstance(operation, RemoveActivity):
            day, index, activity = _find_activity(changed, operation.activity_id)
            _ensure_mutable(activity)
            day.activities.pop(index)

        elif isinstance(operation, MoveActivity):
            source_day, index, activity = _find_activity(changed, operation.activity_id)
            _ensure_mutable(activity)
            source_day.activities.pop(index)
            moved = Activity.model_validate(
                activity.model_copy(update={
                    "starts_at": operation.starts_at,
                    "ends_at": operation.ends_at,
                }).model_dump(mode="python")
            )
            _insert(_find_day(changed, operation.target_day_id), moved, operation.after_activity_id)

    return Trip.model_validate(changed.model_dump(mode="python"))
```

- [ ] **Step 5: Run model and patch tests**

Run:

```powershell
pytest app/tests/test_trip_models.py app/tests/test_trip_patches.py -q
```

Expected: `10 passed`.

- [ ] **Step 6: Commit the protected patch engine**

```powershell
git add backend/app/modules/trips backend/app/tests/test_trip_patches.py
git commit -m "feat: add protected trip patch engine"
```

### Task 3: Add PostgreSQL Snapshot and Revision Tables

**Files:**
- Modify: `backend/app/migrations/init.sql`
- Test: `backend/app/tests/test_trip_schema.py`

- [ ] **Step 1: Write a failing migration contract test**

Create `backend/app/tests/test_trip_schema.py`:

```python
from pathlib import Path


def test_trip_schema_contains_revision_contract():
    sql = (Path(__file__).parents[1] / "migrations" / "init.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS trips" in sql
    assert "current_revision INTEGER NOT NULL" in sql
    assert "snapshot JSONB NOT NULL" in sql
    assert "CREATE TABLE IF NOT EXISTS trip_revisions" in sql
    assert "UNIQUE (trip_id, revision)" in sql
```

- [ ] **Step 2: Run the schema test and verify failure**

Run:

```powershell
pytest app/tests/test_trip_schema.py -q
```

Expected: FAIL because `trips` is absent from `init.sql`.

- [ ] **Step 3: Append the idempotent Trip DDL**

Append to `backend/app/migrations/init.sql`:

```sql

-- Durable Trip aggregate. The JSONB snapshot is the confirmed business state;
-- LangGraph checkpoints remain workflow state only.
CREATE TABLE IF NOT EXISTS trips (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  title VARCHAR(200) NOT NULL,
  destination VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL,
  current_revision INTEGER NOT NULL CHECK (current_revision >= 1),
  snapshot JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trip_revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
  revision INTEGER NOT NULL CHECK (revision >= 1),
  base_revision INTEGER NOT NULL CHECK (base_revision >= 0),
  reason VARCHAR(500) NOT NULL,
  patch JSONB NOT NULL,
  snapshot JSONB NOT NULL,
  created_by UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (trip_id, revision)
);

CREATE INDEX IF NOT EXISTS idx_trips_user_updated
  ON trips(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_trip_revisions_trip_revision
  ON trip_revisions(trip_id, revision DESC);
```

- [ ] **Step 4: Validate the migration contract and a real PostgreSQL schema**

Run:

```powershell
pytest app/tests/test_trip_schema.py -q
docker compose up -d postgres
Get-Content -Raw app/migrations/init.sql | docker compose exec -T postgres psql -U travel_user -d travel_planner
docker compose exec -T postgres psql -U travel_user -d travel_planner -c "\d trips"
docker compose exec -T postgres psql -U travel_user -d travel_planner -c "\d trip_revisions"
```

Expected: pytest reports `1 passed`; the piped migration reports successful or idempotent DDL execution; both `psql` describe commands list the expected columns and constraints.

- [ ] **Step 5: Commit the schema**

```powershell
git add backend/app/migrations/init.sql backend/app/tests/test_trip_schema.py
git commit -m "feat: add trip revision schema"
```

### Task 4: Implement Atomic Trip Persistence

**Files:**
- Create: `backend/app/modules/trips/repository.py`
- Test: `backend/app/tests/test_trip_repository.py`

- [ ] **Step 1: Write PostgreSQL integration tests for create, conflict, history, and restore**

Create `backend/app/tests/test_trip_repository.py` with a fixture that reads `TEST_POSTGRES_URI`, skips when it is absent, applies `init.sql`, creates a unique user, and deletes it after the test. The test body must exercise the public repository methods:

```python
import os
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

from app.modules.trips.errors import RevisionConflictError, TripNotFoundError
from app.modules.trips.models import Activity, Location, TripDay, TripDraft
from app.modules.trips.patches import ActivityChanges, TripPatch, UpdateActivity
from app.modules.trips.repository import TripRepository


@pytest.fixture
async def trip_db():
    uri = os.getenv("TEST_POSTGRES_URI")
    if not uri:
        pytest.skip("TEST_POSTGRES_URI is not configured")
    pool = await asyncpg.create_pool(uri, min_size=1, max_size=2)
    sql = (Path(__file__).parents[1] / "migrations" / "init.sql").read_text(encoding="utf-8")
    async with pool.acquire() as conn:
        await conn.execute(sql)
        user = await conn.fetchrow(
            "INSERT INTO users (username, password_hash) VALUES ($1, 'hash') RETURNING id",
            f"trip-test-{uuid4()}",
        )
    yield pool, str(user["id"])
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM users WHERE id = $1", user["id"])
    await pool.close()


def draft() -> TripDraft:
    return TripDraft(
        title="成都两日游",
        destination="成都",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
        days=[TripDay(
            id="day-1",
            date=date(2026, 8, 1),
            activities=[Activity(
                id="a1",
                name="武侯祠",
                starts_at=datetime(2026, 8, 1, 9),
                ends_at=datetime(2026, 8, 1, 11),
                location=Location(lat=30.64, lng=104.04),
            )],
        )],
    )


@pytest.mark.asyncio
async def test_repository_keeps_immutable_revisions_and_restores(trip_db):
    pool, user_id = trip_db
    repository = TripRepository(pool)
    created = await repository.create(user_id, draft())
    patch = TripPatch(
        base_revision=1,
        scope="activity",
        reason="缩短游览",
        operations=[UpdateActivity(
            activity_id="a1",
            changes=ActivityChanges(ends_at=datetime(2026, 8, 1, 10)),
        )],
    )

    changed = await repository.apply_patch(user_id, created.id, patch)
    assert changed.current_revision == 2
    assert changed.days[0].activities[0].ends_at.hour == 10
    history = await repository.list_revisions(user_id, created.id)
    assert [item.revision for item in history] == [2, 1]

    restored = await repository.restore(user_id, created.id, target_revision=1)
    assert restored.current_revision == 3
    assert restored.days[0].activities[0].ends_at.hour == 11


@pytest.mark.asyncio
async def test_repository_rejects_stale_patch(trip_db):
    pool, user_id = trip_db
    repository = TripRepository(pool)
    created = await repository.create(user_id, draft())
    patch = TripPatch(
        base_revision=2,
        scope="activity",
        reason="stale",
        operations=[UpdateActivity(activity_id="a1", changes=ActivityChanges(cost=10))],
    )
    with pytest.raises(RevisionConflictError):
        await repository.apply_patch(user_id, created.id, patch)


@pytest.mark.asyncio
async def test_repository_never_returns_another_users_trip(trip_db):
    pool, user_id = trip_db
    repository = TripRepository(pool)
    created = await repository.create(user_id, draft())
    with pytest.raises(TripNotFoundError):
        await repository.get(str(uuid4()), created.id)
```

- [ ] **Step 2: Run with the test database and verify the missing repository**

Create a separate `travel_planner_test` database, then run from `backend`:

```powershell
docker compose exec -T postgres createdb -U travel_user travel_planner_test
$env:TEST_POSTGRES_URI='postgresql://travel_user:travel_pass_2026@localhost:5432/travel_planner_test'
pytest app/tests/test_trip_repository.py -q
```

Expected: collection fails because `TripRepository` is not defined. If the database already exists, the `createdb` command reports that fact and the test command remains valid.

- [ ] **Step 3: Implement JSONB serialization and atomic revision transactions**

Create `backend/app/modules/trips/repository.py`. Keep all SQL in this file and implement this public interface exactly:

```python
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg

from app.modules.trips.errors import (
    RevisionConflictError,
    RevisionNotFoundError,
    TripNotFoundError,
)
from app.modules.trips.models import Trip, TripDraft, TripRevisionSummary
from app.modules.trips.patches import TripPatch, apply_trip_patch


def _json(value) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, ensure_ascii=False)


def _load_snapshot(value) -> Trip:
    return Trip.model_validate(json.loads(value) if isinstance(value, str) else value)


class TripRepository:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create(
        self,
        user_id: str,
        draft: TripDraft,
        conversation_id: str | None = None,
    ) -> Trip:
        now = datetime.now(timezone.utc)
        trip = Trip(
            **draft.model_dump(mode="python"),
            id=str(uuid4()),
            user_id=user_id,
            conversation_id=conversation_id,
            current_revision=1,
            created_at=now,
            updated_at=now,
        )
        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "INSERT INTO trips "
                "(id, user_id, conversation_id, title, destination, status, current_revision, snapshot, created_at, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, 1, $7::jsonb, $8, $8)",
                UUID(trip.id), UUID(user_id), UUID(conversation_id) if conversation_id else None,
                trip.title, trip.destination, trip.status.value, _json(trip), now,
            )
            await conn.execute(
                "INSERT INTO trip_revisions "
                "(trip_id, revision, base_revision, reason, patch, snapshot, created_by) "
                "VALUES ($1, 1, 0, 'initial', $2::jsonb, $3::jsonb, $4)",
                UUID(trip.id), _json({"kind": "initial"}), _json(trip), UUID(user_id),
            )
        return trip

    async def get(self, user_id: str, trip_id: str) -> Trip:
        row = await self.pool.fetchrow(
            "SELECT snapshot FROM trips WHERE id = $1 AND user_id = $2",
            UUID(trip_id), UUID(user_id),
        )
        if not row:
            raise TripNotFoundError(trip_id)
        return _load_snapshot(row["snapshot"])

    async def list(self, user_id: str) -> list[Trip]:
        rows = await self.pool.fetch(
            "SELECT snapshot FROM trips WHERE user_id = $1 ORDER BY updated_at DESC",
            UUID(user_id),
        )
        return [_load_snapshot(row["snapshot"]) for row in rows]

    async def apply_patch(self, user_id: str, trip_id: str, patch: TripPatch) -> Trip:
        async with self.pool.acquire() as conn, conn.transaction():
            row = await conn.fetchrow(
                "SELECT current_revision, snapshot FROM trips "
                "WHERE id = $1 AND user_id = $2 FOR UPDATE",
                UUID(trip_id), UUID(user_id),
            )
            if not row:
                raise TripNotFoundError(trip_id)
            if row["current_revision"] != patch.base_revision:
                raise RevisionConflictError(
                    f"expected {row['current_revision']}, got {patch.base_revision}"
                )
            current = _load_snapshot(row["snapshot"])
            changed = apply_trip_patch(current, patch)
            changed.current_revision = current.current_revision + 1
            changed.updated_at = datetime.now(timezone.utc)
            await conn.execute(
                "UPDATE trips SET title = $3, destination = $4, status = $5, "
                "current_revision = $6, snapshot = $7::jsonb, updated_at = $8 "
                "WHERE id = $1 AND user_id = $2",
                UUID(trip_id), UUID(user_id), changed.title, changed.destination,
                changed.status.value, changed.current_revision, _json(changed), changed.updated_at,
            )
            await conn.execute(
                "INSERT INTO trip_revisions "
                "(trip_id, revision, base_revision, reason, patch, snapshot, created_by) "
                "VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7)",
                UUID(trip_id), changed.current_revision, current.current_revision,
                patch.reason, _json(patch), _json(changed), UUID(user_id),
            )
        return changed

    async def list_revisions(self, user_id: str, trip_id: str) -> list[TripRevisionSummary]:
        await self.get(user_id, trip_id)
        rows = await self.pool.fetch(
            "SELECT revision, base_revision, reason, created_at FROM trip_revisions "
            "WHERE trip_id = $1 ORDER BY revision DESC",
            UUID(trip_id),
        )
        return [TripRevisionSummary(**dict(row)) for row in rows]

    async def restore(self, user_id: str, trip_id: str, target_revision: int) -> Trip:
        async with self.pool.acquire() as conn, conn.transaction():
            current_row = await conn.fetchrow(
                "SELECT current_revision, snapshot FROM trips "
                "WHERE id = $1 AND user_id = $2 FOR UPDATE",
                UUID(trip_id), UUID(user_id),
            )
            if not current_row:
                raise TripNotFoundError(trip_id)
            target_row = await conn.fetchrow(
                "SELECT snapshot FROM trip_revisions WHERE trip_id = $1 AND revision = $2",
                UUID(trip_id), target_revision,
            )
            if not target_row:
                raise RevisionNotFoundError(str(target_revision))
            restored = _load_snapshot(target_row["snapshot"])
            restored.current_revision = current_row["current_revision"] + 1
            restored.updated_at = datetime.now(timezone.utc)
            reason = f"restore revision {target_revision}"
            await conn.execute(
                "UPDATE trips SET title = $3, destination = $4, status = $5, "
                "current_revision = $6, snapshot = $7::jsonb, updated_at = $8 "
                "WHERE id = $1 AND user_id = $2",
                UUID(trip_id), UUID(user_id), restored.title, restored.destination,
                restored.status.value, restored.current_revision, _json(restored), restored.updated_at,
            )
            await conn.execute(
                "INSERT INTO trip_revisions "
                "(trip_id, revision, base_revision, reason, patch, snapshot, created_by) "
                "VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7)",
                UUID(trip_id), restored.current_revision, current_row["current_revision"], reason,
                _json({"kind": "restore", "target_revision": target_revision}),
                _json(restored), UUID(user_id),
            )
        return restored
```

- [ ] **Step 4: Run repository and domain tests**

Run:

```powershell
$env:TEST_POSTGRES_URI='postgresql://travel_user:travel_pass_2026@localhost:5432/travel_planner_test'
pytest app/tests/test_trip_models.py app/tests/test_trip_patches.py app/tests/test_trip_repository.py -q
```

Expected: all tests pass, including three PostgreSQL repository tests.

- [ ] **Step 5: Commit persistence**

```powershell
git add backend/app/modules/trips/repository.py backend/app/tests/test_trip_repository.py
git commit -m "feat: persist versioned trip snapshots"
```

### Task 5: Expose Authenticated Trip APIs

**Files:**
- Create: `backend/app/api/schemas/trip.py`
- Create: `backend/app/api/routes/trips.py`
- Modify: `backend/app/main.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/app/tests/test_trips_api.py`

- [ ] **Step 1: Add `httpx` to the development dependencies**

Add the following line to `[project.optional-dependencies].dev` in `backend/pyproject.toml`:

```toml
    "httpx>=0.27.0",
```

Install the development dependencies from `backend`:

```powershell
python -m pip install -e ".[dev]"
```

Expected: pip installs the editable project and its development dependencies without dependency-resolution errors.

- [ ] **Step 2: Write failing route contract tests with dependency overrides**

Create `backend/app/tests/test_trips_api.py`. Use a small FastAPI app so the production lifespan and LLM graph are not started:

```python
from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.trips import get_trip_repository, router
from app.core.auth import get_current_user
from app.modules.trips.errors import RevisionConflictError
from app.modules.trips.models import Trip


def sample_trip() -> Trip:
    now = datetime.now(timezone.utc)
    return Trip(
        id="00000000-0000-0000-0000-000000000001",
        user_id="00000000-0000-0000-0000-000000000002",
        title="成都两日游",
        destination="成都",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
        days=[],
        current_revision=1,
        created_at=now,
        updated_at=now,
    )


class FakeRepository:
    def __init__(self):
        self.trip = sample_trip()

    async def create(self, user_id, draft, conversation_id=None):
        return self.trip

    async def get(self, user_id, trip_id):
        return self.trip

    async def list(self, user_id):
        return [self.trip]

    async def apply_patch(self, user_id, trip_id, patch):
        if patch.base_revision != self.trip.current_revision:
            raise RevisionConflictError("stale revision")
        return self.trip

    async def list_revisions(self, user_id, trip_id):
        return []

    async def restore(self, user_id, trip_id, target_revision):
        return self.trip


def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    repository = FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: {"id": repository.trip.user_id}
    app.dependency_overrides[get_trip_repository] = lambda: repository
    return TestClient(app)


def test_create_and_list_trip_contract():
    api = client()
    response = api.post("/api/trips", json={
        "title": "成都两日游",
        "destination": "成都",
        "start_date": "2026-08-01",
        "end_date": "2026-08-02",
        "party_size": 2,
        "budget_limit": 3000,
        "days": [],
    })
    assert response.status_code == 201
    assert response.json()["current_revision"] == 1
    assert api.get("/api/trips").json()[0]["destination"] == "成都"


def test_stale_patch_maps_to_http_409():
    response = client().post(
        "/api/trips/00000000-0000-0000-0000-000000000001/revisions",
        json={
            "base_revision": 2,
            "scope": "activity",
            "reason": "stale",
            "operations": [{"op": "remove_activity", "activity_id": "a1"}],
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "行程已被更新，请刷新后重试"
```

- [ ] **Step 3: Run the API tests and verify the missing router**

Run:

```powershell
pytest app/tests/test_trips_api.py -q
```

Expected: collection fails because `app.api.routes.trips` does not exist.

- [ ] **Step 4: Add HTTP request schemas**

Create `backend/app/api/schemas/trip.py`:

```python
from typing import Optional

from app.modules.trips.models import TripDraft
from app.modules.trips.patches import TripPatch


class TripCreateRequest(TripDraft):
    conversation_id: Optional[str] = None


class TripPatchRequest(TripPatch):
    pass
```

- [ ] **Step 5: Implement the authenticated routes and error mapping**

Create `backend/app/api/routes/trips.py`:

```python
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.trip import TripCreateRequest, TripPatchRequest
from app.core.auth import get_current_user
from app.core.database import get_db_pool
from app.modules.trips.errors import (
    PatchValidationError,
    RevisionConflictError,
    RevisionNotFoundError,
    TripNotFoundError,
)
from app.modules.trips.models import Trip, TripDraft, TripRevisionSummary
from app.modules.trips.repository import TripRepository

router = APIRouter(prefix="/api/trips", tags=["行程管理"])


async def get_trip_repository() -> TripRepository:
    return TripRepository(await get_db_pool())


def _raise_http(error: Exception):
    if isinstance(error, TripNotFoundError):
        raise HTTPException(status_code=404, detail="行程不存在") from error
    if isinstance(error, RevisionNotFoundError):
        raise HTTPException(status_code=404, detail="行程版本不存在") from error
    if isinstance(error, RevisionConflictError):
        raise HTTPException(status_code=409, detail="行程已被更新，请刷新后重试") from error
    if isinstance(error, PatchValidationError):
        raise HTTPException(status_code=422, detail=str(error)) from error
    raise error


@router.post("", response_model=Trip, status_code=status.HTTP_201_CREATED)
async def create_trip(
    request: TripCreateRequest,
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    values = request.model_dump(exclude={"conversation_id"})
    return await repository.create(
        current_user["id"],
        TripDraft.model_validate(values),
        request.conversation_id,
    )


@router.get("", response_model=list[Trip])
async def list_trips(
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    return await repository.list(current_user["id"])


@router.get("/{trip_id}", response_model=Trip)
async def get_trip(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    try:
        return await repository.get(current_user["id"], trip_id)
    except Exception as error:
        _raise_http(error)


@router.post("/{trip_id}/revisions", response_model=Trip)
async def apply_revision(
    trip_id: str,
    request: TripPatchRequest,
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    try:
        return await repository.apply_patch(current_user["id"], trip_id, request)
    except Exception as error:
        _raise_http(error)


@router.get("/{trip_id}/revisions", response_model=list[TripRevisionSummary])
async def list_revisions(
    trip_id: str,
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    try:
        return await repository.list_revisions(current_user["id"], trip_id)
    except Exception as error:
        _raise_http(error)


@router.post("/{trip_id}/revisions/{revision}/restore", response_model=Trip)
async def restore_revision(
    trip_id: str,
    revision: int,
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    try:
        return await repository.restore(current_user["id"], trip_id, revision)
    except Exception as error:
        _raise_http(error)
```

- [ ] **Step 6: Register the router**

Update imports in `backend/app/main.py`:

```python
from app.api.routes import auth, conversations, history, travel, topology, trips
```

Register it beside the other routers:

```python
app.include_router(trips.router)
```

- [ ] **Step 7: Run API and domain tests**

Run:

```powershell
pytest app/tests/test_trip_models.py app/tests/test_trip_patches.py app/tests/test_trip_schema.py app/tests/test_trips_api.py -q
```

Expected: `13 passed`.

- [ ] **Step 8: Commit the API**

```powershell
git add backend/app/api/schemas/trip.py backend/app/api/routes/trips.py backend/app/main.py backend/pyproject.toml backend/app/tests/test_trips_api.py
git commit -m "feat: expose versioned trip api"
```

### Task 6: Document and Verify the First Deliverable

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add Trip API documentation**

Add this subsection after the existing travel API section in `README.md`:

```markdown
### 行程管理 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/trips` | 创建持久化 Trip 和初始版本 |
| GET | `/api/trips` | 获取当前用户的 Trip 列表 |
| GET | `/api/trips/{trip_id}` | 获取 Trip 当前快照 |
| POST | `/api/trips/{trip_id}/revisions` | 基于当前版本应用结构化补丁 |
| GET | `/api/trips/{trip_id}/revisions` | 获取不可变版本历史 |
| POST | `/api/trips/{trip_id}/revisions/{revision}/restore` | 将历史快照恢复为一个新版本 |

补丁请求必须包含 `base_revision`。版本不一致返回 HTTP 409；锁定或已完成活动被修改时返回 HTTP 422。恢复历史版本不会删除后续历史，而是创建一个新的当前版本。
```

- [ ] **Step 2: Run static and unit verification**

Run from `backend`:

```powershell
ruff check app/modules/trips app/api/routes/trips.py app/api/schemas/trip.py app/tests/test_trip_*.py
pytest app/tests/test_trip_models.py app/tests/test_trip_patches.py app/tests/test_trip_schema.py app/tests/test_trips_api.py -q
```

Expected: Ruff exits successfully and all non-integration Trip tests pass.

- [ ] **Step 3: Run PostgreSQL integration and full backend regression tests**

Run:

```powershell
$env:TEST_POSTGRES_URI='postgresql://travel_user:travel_pass_2026@localhost:5432/travel_planner_test'
pytest app/tests/test_trip_repository.py -q
pytest -q
```

Expected: repository integration tests pass. The full backend suite has no new failures; pre-existing environment-dependent tests may skip with their documented reason.

- [ ] **Step 4: Exercise the authenticated API manually**

Start the backend with the project's existing local command, register or log in, and use the Swagger UI at `http://localhost:8000/docs` to:

1. Create a two-day Trip.
2. Fetch it and record `current_revision = 1`.
3. Apply a valid activity update with `base_revision = 1` and observe revision 2.
4. Repeat the old patch with `base_revision = 1` and observe HTTP 409.
5. Restore revision 1 and observe a new revision 3.

Expected: the current snapshot follows steps 3 and 5, while the revision list retains versions 1, 2, and 3.

- [ ] **Step 5: Commit documentation and verification results**

```powershell
git add README.md
git commit -m "docs: document versioned trip api"
git status --short
```

Expected: the commit succeeds and `git status --short` is empty.
