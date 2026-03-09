import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import aioredis
from pydantic import BaseModel
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

RATE_LIMIT = 100        # max requests
WINDOW_SECONDS = 60     # sliding window duration


class Settings(BaseSettings):
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/1")

    class Config:
        env_file = ".env"


settings = Settings()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RateLimitCheck(BaseModel):
    client_id: str


class RateLimitResult(BaseModel):
    allowed: bool
    remaining: int
    reset_at: datetime
    current_usage: int
    limit: int
    window_seconds: int


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class RateLimitService:
    """
    Sliding-window rate limiter using Redis sorted sets.

    Each request is recorded as a member of a sorted set keyed by client_id.
    The score is the request timestamp (epoch seconds with sub-second precision).
    On every check we remove members older than window_seconds, then count
    what remains. If the count is below the limit the request is allowed and a
    new entry is added.
    """

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def init_redis(self):
        try:
            self.redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self.redis.ping()
            logger.info("Redis connection established for rate limiter.")
        except Exception as exc:
            logger.error("Failed to connect to Redis: %s", exc)
            self.redis = None

    async def close(self):
        if self.redis:
            await self.redis.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _key(self, client_id: str) -> str:
        return f"ratelimit:{client_id}"

    def _reset_at(self) -> datetime:
        """The earliest time when the window fully resets (now + window)."""
        return datetime.fromtimestamp(
            time.time() + WINDOW_SECONDS, tz=timezone.utc
        )

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def check(self, client_id: str) -> RateLimitResult:
        if not self.redis:
            raise RuntimeError("Redis unavailable")

        key = self._key(client_id)
        now = time.time()
        window_start = now - WINDOW_SECONDS

        # Use a pipeline for atomicity
        pipe = self.redis.pipeline(transaction=True)

        # Remove timestamps older than the sliding window
        pipe.zremrangebyscore(key, "-inf", window_start)
        # Count remaining entries in the window
        pipe.zcard(key)
        results = await pipe.execute()

        current_usage: int = results[1]

        if current_usage < RATE_LIMIT:
            # Allow — record this request
            member = f"{now:.6f}"
            await self.redis.zadd(key, {member: now})
            # Keep key alive for at least one window
            await self.redis.expire(key, WINDOW_SECONDS + 1)
            current_usage += 1
            allowed = True
        else:
            allowed = False

        remaining = max(0, RATE_LIMIT - current_usage)
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_at=self._reset_at(),
            current_usage=current_usage,
            limit=RATE_LIMIT,
            window_seconds=WINDOW_SECONDS,
        )

    async def status(self, client_id: str) -> RateLimitResult:
        """Read current usage without recording a new request."""
        if not self.redis:
            raise RuntimeError("Redis unavailable")

        key = self._key(client_id)
        now = time.time()
        window_start = now - WINDOW_SECONDS

        await self.redis.zremrangebyscore(key, "-inf", window_start)
        current_usage: int = await self.redis.zcard(key)

        remaining = max(0, RATE_LIMIT - current_usage)
        return RateLimitResult(
            allowed=current_usage < RATE_LIMIT,
            remaining=remaining,
            reset_at=self._reset_at(),
            current_usage=current_usage,
            limit=RATE_LIMIT,
            window_seconds=WINDOW_SECONDS,
        )

    async def reset(self, client_id: str) -> dict:
        """Clear all rate limit entries for a client."""
        if not self.redis:
            raise RuntimeError("Redis unavailable")
        deleted = await self.redis.delete(self._key(client_id))
        return {
            "client_id": client_id,
            "reset": True,
            "entries_removed": deleted,
        }
