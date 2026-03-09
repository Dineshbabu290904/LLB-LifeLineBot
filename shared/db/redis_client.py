import aioredis
from typing import Optional, Any
import json
import logging

logger = logging.getLogger(__name__)

_redis: Optional[aioredis.Redis] = None


async def get_redis_client(redis_url: str) -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = await aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
        )
        logger.info("Redis client initialized")
    return _redis


async def close_redis_client():
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
        logger.info("Redis client closed")


class RedisCache:
    def __init__(self, redis: aioredis.Redis, prefix: str = "medbot"):
        self.redis = redis
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        value = await self.redis.get(self._key(key))
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        return await self.redis.setex(self._key(key), ttl, serialized)

    async def delete(self, key: str) -> int:
        return await self.redis.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return bool(await self.redis.exists(self._key(key)))

    async def increment(self, key: str) -> int:
        return await self.redis.incr(self._key(key))

    async def expire(self, key: str, ttl: int) -> bool:
        return await self.redis.expire(self._key(key), ttl)
