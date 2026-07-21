"""PostgreSQL provider cache tests."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.modules.providers.cache import PostgresProviderCache
from app.modules.providers.models import GeoPoint, ProviderMeta, ProviderResult


class FakePool:
    def __init__(self):
        self.fetchrow = AsyncMock()
        self.execute = AsyncMock()


def result() -> ProviderResult[GeoPoint]:
    return ProviderResult(
        data=GeoPoint(lat=30.57, lng=104.06, address="成都"),
        meta=ProviderMeta(provider="amap", fetched_at=datetime.now(timezone.utc)),
    )


@pytest.mark.asyncio
async def test_postgres_cache_reads_expired_rows_for_stale_fallback():
    pool = FakePool()
    cached = result()
    now = datetime.now(timezone.utc)
    pool.fetchrow.return_value = {
        "cache_key": "geocode:key",
        "data_type": "geocode",
        "payload": json.dumps(cached.model_dump(mode="json"), ensure_ascii=False),
        "fetched_at": now - timedelta(hours=2),
        "expires_at": now - timedelta(hours=1),
    }
    cache = PostgresProviderCache(pool)

    entry = await cache.get("geocode:key")

    assert entry is not None
    assert entry.is_stale(now) is True
    assert entry.payload["meta"]["provider"] == "amap"


@pytest.mark.asyncio
async def test_postgres_cache_upserts_structured_result():
    pool = FakePool()
    cache = PostgresProviderCache(pool)

    await cache.set("geocode:key", "geocode", result(), ttl_seconds=3600)

    pool.execute.assert_awaited_once()
    sql = pool.execute.await_args.args[0]
    assert "INSERT INTO provider_cache" in sql
    assert "ON CONFLICT (cache_key)" in sql
