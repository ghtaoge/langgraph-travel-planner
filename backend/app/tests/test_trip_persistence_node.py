"""PlanningGraph persist_trip node tests."""

from datetime import date

import pytest

from app.modules.planner import nodes
from app.modules.trips.models import Trip, TripDraft

USER_ID = "00000000-0000-0000-0000-000000000002"
THREAD_ID = "00000000-0000-0000-0000-000000000003"
TRIP_ID = "00000000-0000-0000-0000-000000000001"


def draft() -> TripDraft:
    return TripDraft(
        title="成都一日游",
        destination="成都",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 1),
        days=[],
    )


def trip() -> Trip:
    return Trip(**draft().model_dump(), id=TRIP_ID, user_id=USER_ID)


class FakeRepository:
    def __init__(self, existing=None):
        self.existing = existing
        self.create_calls = 0

    async def find_by_conversation(self, user_id, conversation_id):
        return self.existing

    async def create(self, user_id, trip_draft, conversation_id=None):
        self.create_calls += 1
        return trip()


@pytest.mark.asyncio
async def test_persist_trip_creates_first_confirmed_snapshot(monkeypatch):
    repository = FakeRepository()
    monkeypatch.setattr(nodes, "_db_pool", object())
    monkeypatch.setattr(nodes, "TripRepository", lambda pool: repository)
    monkeypatch.setattr(nodes, "build_trip_draft", lambda state: draft())

    result = await nodes.persist_trip_node({
        "user_id": USER_ID,
        "thread_id": THREAD_ID,
        "approval_status": "approved",
    })

    assert result["trip_id"] == TRIP_ID
    assert result["trip_revision"] == 1
    assert result["trip_snapshot"]["destination"] == "成都"
    assert repository.create_calls == 1


@pytest.mark.asyncio
async def test_persist_trip_reuses_existing_conversation_trip(monkeypatch):
    repository = FakeRepository(existing=trip())
    monkeypatch.setattr(nodes, "_db_pool", object())
    monkeypatch.setattr(nodes, "TripRepository", lambda pool: repository)

    result = await nodes.persist_trip_node({
        "user_id": USER_ID,
        "thread_id": THREAD_ID,
        "approval_status": "approved",
    })

    assert result["trip_id"] == TRIP_ID
    assert repository.create_calls == 0
