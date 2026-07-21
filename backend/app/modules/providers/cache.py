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
