"""Provider cache contract and in-memory implementation."""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.modules.providers.models import CacheEntry, ProviderResult


def cache_key(data_type: str, parameters: dict) -> str:
    canonical = json.dumps(parameters, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{data_type}:{digest}"


class ProviderCache(Protocol):
    async def get(self, key: str) -> CacheEntry | None: ...

    async def set(
        self,
        key: str,
        data_type: str,
        result: ProviderResult,
        ttl_seconds: int,
    ) -> None: ...


class MemoryProviderCache:
    def __init__(self):
        self.entries: dict[str, CacheEntry] = {}

    async def get(self, key: str) -> CacheEntry | None:
        return self.entries.get(key)

    async def set(
        self,
        key: str,
        data_type: str,
        result: ProviderResult,
        ttl_seconds: int,
    ) -> None:
        now = datetime.now(timezone.utc)
        self.entries[key] = CacheEntry(
            key=key,
            data_type=data_type,
            payload=result.model_dump(mode="json"),
            fetched_at=result.meta.fetched_at,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )


class PostgresProviderCache:
    def __init__(self, pool):
        self.pool = pool

    async def get(self, key: str) -> CacheEntry | None:
        row = await self.pool.fetchrow(
            "SELECT cache_key, data_type, payload, fetched_at, expires_at "
            "FROM provider_cache WHERE cache_key = $1",
            key,
        )
        if not row:
            return None
        payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
        return CacheEntry(
            key=row["cache_key"],
            data_type=row["data_type"],
            payload=payload,
            fetched_at=row["fetched_at"],
            expires_at=row["expires_at"],
        )

    async def set(
        self,
        key: str,
        data_type: str,
        result: ProviderResult,
        ttl_seconds: int,
    ) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        payload = json.dumps(result.model_dump(mode="json"), ensure_ascii=False)
        await self.pool.execute(
            "INSERT INTO provider_cache "
            "(cache_key, provider, data_type, payload, fetched_at, expires_at, updated_at) "
            "VALUES ($1, $2, $3, $4::jsonb, $5, $6, NOW()) "
            "ON CONFLICT (cache_key) DO UPDATE SET "
            "provider = EXCLUDED.provider, data_type = EXCLUDED.data_type, "
            "payload = EXCLUDED.payload, fetched_at = EXCLUDED.fetched_at, "
            "expires_at = EXCLUDED.expires_at, updated_at = NOW()",
            key,
            result.meta.provider,
            data_type,
            payload,
            result.meta.fetched_at,
            expires_at,
        )
