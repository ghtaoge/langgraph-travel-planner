"""HTTP request schemas for Trip APIs."""

from typing import Optional
from uuid import UUID

from app.modules.trips.models import TripDraft
from app.modules.trips.patches import TripPatch


class TripCreateRequest(TripDraft):
    conversation_id: Optional[UUID] = None


class TripPatchRequest(TripPatch):
    pass
