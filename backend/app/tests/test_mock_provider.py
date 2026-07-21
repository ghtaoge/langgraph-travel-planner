"""Deterministic Mock travel provider tests."""

from datetime import date

import pytest

from app.modules.providers.mock import MockTravelProvider


@pytest.mark.asyncio
async def test_mock_provider_marks_all_data_as_estimated():
    provider = MockTravelProvider()

    geocode = await provider.geocode("武侯祠", "成都")
    pois = await provider.search_pois("成都", "文化", limit=2)
    weather = await provider.weather("成都", date(2026, 8, 1))
    route = await provider.route(geocode.data, pois.data[0].location)

    assert geocode.meta.estimated is True
    assert pois.meta.estimated is True
    assert weather.meta.estimated is True
    assert route.meta.estimated is True
    assert len(pois.data) == 2
    assert route.data.distance_m >= 0


@pytest.mark.asyncio
async def test_mock_provider_is_deterministic_for_same_input():
    provider = MockTravelProvider()

    first = await provider.geocode("未知景点", "苏州")
    second = await provider.geocode("未知景点", "苏州")

    assert first.data == second.data
