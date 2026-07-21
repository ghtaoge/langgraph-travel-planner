"""Authenticated Trip CRUD and revision endpoints."""

from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.schemas.trip import TripCreateRequest, TripPatchRequest
from app.core.auth import get_current_user
from app.core.database import get_db_pool
from app.modules.trips.errors import (
    PatchValidationError,
    RevisionConflictError,
    RevisionNotFoundError,
    TripError,
    TripNotFoundError,
)
from app.modules.trips.models import Trip, TripDraft, TripRevisionSummary
from app.modules.trips.repository import TripRepository

router = APIRouter(prefix="/api/trips", tags=["行程管理"])


async def get_trip_repository() -> TripRepository:
    return TripRepository(await get_db_pool())


def _raise_http(error: TripError) -> NoReturn:
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
    try:
        return await repository.create(
            current_user["id"],
            TripDraft.model_validate(values),
            str(request.conversation_id) if request.conversation_id else None,
        )
    except TripError as error:
        _raise_http(error)


@router.get("", response_model=list[Trip])
async def list_trips(
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    return await repository.list(current_user["id"])


@router.get("/{trip_id}", response_model=Trip)
async def get_trip(
    trip_id: UUID,
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    try:
        return await repository.get(current_user["id"], str(trip_id))
    except TripError as error:
        _raise_http(error)


@router.post("/{trip_id}/revisions", response_model=Trip)
async def apply_revision(
    trip_id: UUID,
    request: TripPatchRequest,
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    try:
        return await repository.apply_patch(current_user["id"], str(trip_id), request)
    except TripError as error:
        _raise_http(error)


@router.get("/{trip_id}/revisions", response_model=list[TripRevisionSummary])
async def list_revisions(
    trip_id: UUID,
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    try:
        return await repository.list_revisions(current_user["id"], str(trip_id))
    except TripError as error:
        _raise_http(error)


@router.post("/{trip_id}/revisions/{revision}/restore", response_model=Trip)
async def restore_revision(
    trip_id: UUID,
    revision: int,
    current_user: dict = Depends(get_current_user),
    repository: TripRepository = Depends(get_trip_repository),
):
    try:
        return await repository.restore(current_user["id"], str(trip_id), revision)
    except TripError as error:
        _raise_http(error)
