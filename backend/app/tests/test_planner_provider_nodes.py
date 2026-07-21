"""PlanningGraph provider research and enrichment tests."""

from datetime import date

import pytest

from app.modules.planner.provider_nodes import enrich_itinerary_node, provider_research_node
from app.modules.providers.cache import MemoryProviderCache
from app.modules.providers.factory import set_travel_data_service
from app.modules.providers.mock import MockTravelProvider
from app.modules.providers.service import TravelDataService


@pytest.fixture(autouse=True)
def provider_service():
    provider = MockTravelProvider()
    service = TravelDataService(provider, provider, MemoryProviderCache())
    set_travel_data_service(service)
    yield service
    set_travel_data_service(None)


@pytest.mark.asyncio
async def test_provider_research_adds_structured_pois():
    result = await provider_research_node({
        "destination": "成都",
        "travel_style": "文化游",
    })

    provider_data = result["research_result"]["_provider"]
    assert provider_data["pois"][0]["name"] == "武侯祠"
    assert provider_data["meta"]["estimated"] is True


@pytest.mark.asyncio
async def test_enrichment_geocodes_activities_and_builds_weather_routes():
    state = {
        "thread_id": "thread-1",
        "destination": "成都",
        "start_date": date(2026, 8, 1),
        "itinerary": {
            "daily_plans": [{
                "day": 1,
                "date": "2026-08-01",
                "activities": [
                    {"name": "武侯祠", "time": "09:00-11:00", "cost": 50, "location": "武侯祠"},
                    {"name": "杜甫草堂", "time": "13:00-15:00", "cost": 50, "location": "杜甫草堂"},
                ],
            }],
        },
    }

    result = await enrich_itinerary_node(state)

    day = result["itinerary"]["daily_plans"][0]
    first = day["activities"][0]
    assert first["id"]
    assert first["location"]["lat"] != 0
    assert first["source"]["provider"] == "mock"
    assert day["weather"]["date"] == "2026-08-01"
    assert day["route_legs"][0]["from_activity_id"] == first["id"]
    assert result["provider_warnings"]
