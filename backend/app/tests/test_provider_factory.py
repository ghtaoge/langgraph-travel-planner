"""Provider service lifecycle tests."""

import pytest

from app.config.settings import settings
from app.modules.providers.factory import (
    close_travel_data_service,
    get_travel_data_service,
    init_travel_data_service,
)
from app.modules.providers.mock import MockTravelProvider


@pytest.mark.asyncio
async def test_factory_uses_mock_when_amap_key_is_empty(monkeypatch):
    monkeypatch.setattr(settings, "AMAP_API_KEY", "")
    pool = object()

    service = await init_travel_data_service(pool)

    assert isinstance(service.primary, MockTravelProvider)
    assert get_travel_data_service() is service
    await close_travel_data_service()
