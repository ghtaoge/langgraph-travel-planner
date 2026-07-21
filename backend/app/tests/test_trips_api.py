"""Authenticated Trip API contract tests."""

from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.trips import get_trip_repository, router
from app.core.auth import get_current_user
from app.modules.trips.errors import (
    ProtectedActivityError,
    RevisionConflictError,
    TripNotFoundError,
)
from app.modules.trips.models import Trip

TRIP_ID = "00000000-0000-0000-0000-000000000001"
USER_ID = "00000000-0000-0000-0000-000000000002"


def sample_trip() -> Trip:
    now = datetime.now(timezone.utc)
    return Trip(
        id=TRIP_ID,
        user_id=USER_ID,
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
        self.patch_error = None

    async def create(self, user_id, draft, conversation_id=None):
        assert user_id == USER_ID
        return self.trip

    async def get(self, user_id, trip_id):
        if trip_id != TRIP_ID:
            raise TripNotFoundError(trip_id)
        return self.trip

    async def list(self, user_id):
        return [self.trip]

    async def apply_patch(self, user_id, trip_id, patch):
        if self.patch_error:
            raise self.patch_error
        return self.trip

    async def list_revisions(self, user_id, trip_id):
        return []

    async def restore(self, user_id, trip_id, target_revision):
        return self.trip


def make_client(repository: FakeRepository | None = None) -> tuple[TestClient, FakeRepository]:
    app = FastAPI()
    app.include_router(router)
    repository = repository or FakeRepository()
    app.dependency_overrides[get_current_user] = lambda: {"id": USER_ID}
    app.dependency_overrides[get_trip_repository] = lambda: repository
    return TestClient(app), repository


def test_create_and_list_trip_contract():
    client, _ = make_client()
    response = client.post(
        "/api/trips",
        json={
            "title": "成都两日游",
            "destination": "成都",
            "start_date": "2026-08-01",
            "end_date": "2026-08-02",
            "party_size": 2,
            "budget_limit": 3000,
            "days": [],
        },
    )

    assert response.status_code == 201
    assert response.json()["current_revision"] == 1
    assert client.get("/api/trips").json()[0]["destination"] == "成都"


def test_get_missing_trip_maps_to_http_404():
    client, _ = make_client()

    response = client.get("/api/trips/00000000-0000-0000-0000-000000000099")

    assert response.status_code == 404
    assert response.json()["detail"] == "行程不存在"


def test_stale_patch_maps_to_http_409():
    repository = FakeRepository()
    repository.patch_error = RevisionConflictError("stale revision")
    client, _ = make_client(repository)

    response = client.post(
        f"/api/trips/{TRIP_ID}/revisions",
        json={
            "base_revision": 1,
            "scope": "activity",
            "reason": "stale",
            "operations": [{"op": "remove_activity", "activity_id": "a1"}],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "行程已被更新，请刷新后重试"


def test_protected_patch_maps_to_http_422():
    repository = FakeRepository()
    repository.patch_error = ProtectedActivityError("activity is protected: a1")
    client, _ = make_client(repository)

    response = client.post(
        f"/api/trips/{TRIP_ID}/revisions",
        json={
            "base_revision": 1,
            "scope": "activity",
            "reason": "remove",
            "operations": [{"op": "remove_activity", "activity_id": "a1"}],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "activity is protected: a1"


def test_invalid_trip_id_is_rejected_before_repository_call():
    client, _ = make_client()

    response = client.get("/api/trips/not-a-uuid")

    assert response.status_code == 422


def test_production_app_registers_trip_routes():
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/api/trips" in paths
    assert "/api/trips/{trip_id}/revisions" in paths
