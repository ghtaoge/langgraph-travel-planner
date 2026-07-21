"""HTTP request schemas for Trip APIs."""

from typing import Optional

from app.modules.trips.models import TripDraft
from app.modules.trips.patches import TripPatch


class TripCreateRequest(TripDraft):
    conversation_id: Optional[str] = None


class TripPatchRequest(TripPatch):
    pass
