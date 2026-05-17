import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

log = structlog.get_logger()

PIPELINE_CHANNEL = "nexus:pipeline:events"
AGENT_CHANNEL = "nexus:agent:events"
INCIDENT_CHANNEL = "nexus:incident:events"


class RedisPool:
    _client: aioredis.Redis | None = None

    async def initialize(self) -> None:
        self._client = await aioredis.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_POOL_SIZE,
            encoding="utf-8",
            decode_responses=True,
        )
        log.info("redis.connected", url=settings.REDIS_URL)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis not initialized")
        return self._client

    # ── Cache helpers ─────────────────────────────────────────────────────────
    async def get(self, key: str) -> Any | None:
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        await self.client.setex(key, ttl, json.dumps(value, default=str))

    async def delete(self, key: str) -> None:
        await self.client.delete(key)

    async def invalidate_prefix(self, prefix: str) -> None:
        keys = await self.client.keys(f"{prefix}:*")
        if keys:
            await self.client.delete(*keys)

    # ── Pub/Sub ───────────────────────────────────────────────────────────────
    async def publish(self, channel: str, event: dict) -> None:
        await self.client.publish(channel, json.dumps(event, default=str))

    async def subscribe(self, *channels: str):
        pubsub = self.client.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub

    # ── Rate limiting (token bucket) ──────────────────────────────────────────
    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        results = await pipe.execute()
        return int(results[0]) <= limit


redis_pool = RedisPool()
