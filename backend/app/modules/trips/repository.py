"""Atomic PostgreSQL persistence for current Trip snapshots and revisions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg

from app.modules.trips.errors import (
    PatchValidationError,
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
    payload = json.loads(value) if isinstance(value, str) else value
    return Trip.model_validate(payload)


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

        async with self.pool.acquire() as connection, connection.transaction():
            if conversation_id:
                owns_conversation = await connection.fetchval(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM conversations WHERE id = $1 AND user_id = $2"
                    ")",
                    UUID(conversation_id),
                    UUID(user_id),
                )
                if not owns_conversation:
                    raise PatchValidationError("conversation not found or not owned by user")
            await connection.execute(
                "INSERT INTO trips "
                "(id, user_id, conversation_id, title, destination, status, "
                "current_revision, snapshot, created_at, updated_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, 1, $7::jsonb, $8, $8)",
                UUID(trip.id),
                UUID(user_id),
                UUID(conversation_id) if conversation_id else None,
                trip.title,
                trip.destination,
                trip.status.value,
                _json(trip),
                now,
            )
            await connection.execute(
                "INSERT INTO trip_revisions "
                "(trip_id, revision, base_revision, reason, patch, snapshot, created_by) "
                "VALUES ($1, 1, 0, 'initial', $2::jsonb, $3::jsonb, $4)",
                UUID(trip.id),
                _json({"kind": "initial"}),
                _json(trip),
                UUID(user_id),
            )
        return trip

    async def get(self, user_id: str, trip_id: str) -> Trip:
        row = await self.pool.fetchrow(
            "SELECT snapshot FROM trips WHERE id = $1 AND user_id = $2",
            UUID(trip_id),
            UUID(user_id),
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

    async def find_by_conversation(self, user_id: str, conversation_id: str) -> Trip | None:
        row = await self.pool.fetchrow(
            "SELECT snapshot FROM trips WHERE user_id = $1 AND conversation_id = $2",
            UUID(user_id),
            UUID(conversation_id),
        )
        return _load_snapshot(row["snapshot"]) if row else None

    async def apply_patch(self, user_id: str, trip_id: str, patch: TripPatch) -> Trip:
        async with self.pool.acquire() as connection, connection.transaction():
            row = await connection.fetchrow(
                "SELECT current_revision, snapshot FROM trips "
                "WHERE id = $1 AND user_id = $2 FOR UPDATE",
                UUID(trip_id),
                UUID(user_id),
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
            await self._write_revision(
                connection=connection,
                user_id=user_id,
                trip=changed,
                base_revision=current.current_revision,
                reason=patch.reason,
                patch_payload=patch,
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
        async with self.pool.acquire() as connection, connection.transaction():
            current_row = await connection.fetchrow(
                "SELECT current_revision FROM trips "
                "WHERE id = $1 AND user_id = $2 FOR UPDATE",
                UUID(trip_id),
                UUID(user_id),
            )
            if not current_row:
                raise TripNotFoundError(trip_id)

            target_row = await connection.fetchrow(
                "SELECT snapshot FROM trip_revisions WHERE trip_id = $1 AND revision = $2",
                UUID(trip_id),
                target_revision,
            )
            if not target_row:
                raise RevisionNotFoundError(str(target_revision))

            restored = _load_snapshot(target_row["snapshot"])
            restored.current_revision = current_row["current_revision"] + 1
            restored.updated_at = datetime.now(timezone.utc)
            await self._write_revision(
                connection=connection,
                user_id=user_id,
                trip=restored,
                base_revision=current_row["current_revision"],
                reason=f"restore revision {target_revision}",
                patch_payload={"kind": "restore", "target_revision": target_revision},
            )
        return restored

    @staticmethod
    async def _write_revision(
        connection,
        user_id: str,
        trip: Trip,
        base_revision: int,
        reason: str,
        patch_payload,
    ) -> None:
        await connection.execute(
            "UPDATE trips SET title = $3, destination = $4, status = $5, "
            "current_revision = $6, snapshot = $7::jsonb, updated_at = $8 "
            "WHERE id = $1 AND user_id = $2",
            UUID(trip.id),
            UUID(user_id),
            trip.title,
            trip.destination,
            trip.status.value,
            trip.current_revision,
            _json(trip),
            trip.updated_at,
        )
        await connection.execute(
            "INSERT INTO trip_revisions "
            "(trip_id, revision, base_revision, reason, patch, snapshot, created_by) "
            "VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7)",
            UUID(trip.id),
            trip.current_revision,
            base_revision,
            reason,
            _json(patch_payload),
            _json(trip),
            UUID(user_id),
        )
