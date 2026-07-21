"""TripRepository transaction tests with controlled asyncpg doubles."""

from datetime import date, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.modules.trips.errors import PatchValidationError, RevisionConflictError, TripNotFoundError
from app.modules.trips.models import Activity, Location, Trip, TripDay, TripDraft
from app.modules.trips.patches import ActivityChanges, TripPatch, UpdateActivity
from app.modules.trips.repository import TripRepository, _json, _load_snapshot

USER_ID = "00000000-0000-0000-0000-000000000002"
TRIP_ID = "00000000-0000-0000-0000-000000000001"


class AsyncContext:
    def __init__(self, value=None):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeConnection:
    def __init__(self):
        self.fetchrow = AsyncMock()
        self.fetchval = AsyncMock()
        self.execute = AsyncMock()

    def transaction(self):
        return AsyncContext()


class FakePool:
    def __init__(self, connection=None):
        self.connection = connection or FakeConnection()
        self.fetchrow = AsyncMock()
        self.fetch = AsyncMock()

    def acquire(self):
        return AsyncContext(self.connection)


def draft() -> TripDraft:
    return TripDraft(
        title="成都两日游",
        destination="成都",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 2),
        days=[
            TripDay(
                id="day-1",
                date=date(2026, 8, 1),
                activities=[
                    Activity(
                        id="a1",
                        name="武侯祠",
                        starts_at=datetime(2026, 8, 1, 9),
                        ends_at=datetime(2026, 8, 1, 11),
                        location=Location(lat=30.64, lng=104.04),
                    )
                ],
            )
        ],
    )


def persisted_trip() -> Trip:
    return Trip(
        **draft().model_dump(mode="python"),
        id=TRIP_ID,
        user_id=USER_ID,
        current_revision=1,
    )


def patch(base_revision: int = 1) -> TripPatch:
    return TripPatch(
        base_revision=base_revision,
        scope="activity",
        reason="缩短游览",
        operations=[
            UpdateActivity(
                activity_id="a1",
                changes=ActivityChanges(ends_at=datetime(2026, 8, 1, 10)),
            )
        ],
    )


def test_snapshot_json_round_trip():
    original = persisted_trip()

    restored = _load_snapshot(_json(original))

    assert restored == original


@pytest.mark.asyncio
async def test_create_writes_current_and_initial_revision():
    connection = FakeConnection()
    repository = TripRepository(FakePool(connection))

    created = await repository.create(USER_ID, draft())

    assert UUID(created.id)
    assert created.current_revision == 1
    assert connection.execute.await_count == 2
    assert "INSERT INTO trips" in connection.execute.await_args_list[0].args[0]
    assert "INSERT INTO trip_revisions" in connection.execute.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_create_rejects_conversation_not_owned_by_user():
    connection = FakeConnection()
    connection.fetchval.return_value = None
    repository = TripRepository(FakePool(connection))

    with pytest.raises(PatchValidationError, match="conversation"):
        await repository.create(
            USER_ID,
            draft(),
            conversation_id="00000000-0000-0000-0000-000000000099",
        )

    connection.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_apply_patch_increments_revision_in_one_transaction():
    connection = FakeConnection()
    connection.fetchrow.return_value = {
        "current_revision": 1,
        "snapshot": _json(persisted_trip()),
    }
    repository = TripRepository(FakePool(connection))

    changed = await repository.apply_patch(USER_ID, TRIP_ID, patch())

    assert changed.current_revision == 2
    assert changed.days[0].activities[0].ends_at.hour == 10
    assert connection.execute.await_count == 2


@pytest.mark.asyncio
async def test_apply_patch_rejects_stale_revision_before_writing():
    connection = FakeConnection()
    connection.fetchrow.return_value = {
        "current_revision": 1,
        "snapshot": _json(persisted_trip()),
    }
    repository = TripRepository(FakePool(connection))

    with pytest.raises(RevisionConflictError):
        await repository.apply_patch(USER_ID, TRIP_ID, patch(base_revision=2))

    connection.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_never_returns_another_users_trip():
    pool = FakePool()
    pool.fetchrow.return_value = None
    repository = TripRepository(pool)

    with pytest.raises(TripNotFoundError):
        await repository.get("00000000-0000-0000-0000-000000000003", TRIP_ID)


@pytest.mark.asyncio
async def test_restore_creates_new_revision_without_deleting_history():
    connection = FakeConnection()
    connection.fetchrow.side_effect = [
        {"current_revision": 2},
        {"snapshot": _json(persisted_trip())},
    ]
    repository = TripRepository(FakePool(connection))

    restored = await repository.restore(USER_ID, TRIP_ID, target_revision=1)

    assert restored.current_revision == 3
    assert connection.execute.await_count == 2
    assert all("DELETE" not in call.args[0] for call in connection.execute.await_args_list)
