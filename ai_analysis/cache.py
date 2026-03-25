from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from config import settings


class AnalysisCache:
    def __init__(self):
        self.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def get_json(self, key: str) -> dict[str, Any] | None:
        raw = await self.redis.get(key)
        if not raw:
            return None
        return json.loads(raw)

    async def set_json(self, key: str, payload: dict[str, Any], ttl_seconds: int) -> None:
        await self.redis.set(key, json.dumps(payload, ensure_ascii=False), ex=ttl_seconds)

    async def close(self) -> None:
        await self.redis.aclose()
