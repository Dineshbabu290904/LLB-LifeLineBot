import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aioredis
from pydantic import BaseModel
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

SESSION_TTL = 3600  # seconds


class Settings(BaseSettings):
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

    class Config:
        env_file = ".env"


settings = Settings()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SessionCreate(BaseModel):
    user_id: str
    preferences: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionUpdate(BaseModel):
    conversation_context: Optional[list] = None
    preferences: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionData(BaseModel):
    session_id: str
    user_id: str
    conversation_context: list = []
    preferences: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}
    created_at: str
    updated_at: str
    expires_at: str


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SessionService:
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
            logger.info("Redis connection established.")
        except Exception as exc:
            logger.error("Failed to connect to Redis: %s", exc)
            self.redis = None

    async def close(self):
        if self.redis:
            await self.redis.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _session_key(self, session_id: str) -> str:
        return f"session:{session_id}"

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _expires_iso(self) -> str:
        from datetime import timedelta
        return (datetime.now(timezone.utc) + timedelta(seconds=SESSION_TTL)).isoformat()

    async def _get_raw(self, session_id: str) -> Optional[dict]:
        if not self.redis:
            raise RuntimeError("Redis unavailable")
        raw = await self.redis.get(self._session_key(session_id))
        if raw is None:
            return None
        return json.loads(raw)

    async def _save(self, data: dict) -> None:
        if not self.redis:
            raise RuntimeError("Redis unavailable")
        key = self._session_key(data["session_id"])
        await self.redis.setex(key, SESSION_TTL, json.dumps(data))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create_session(self, payload: SessionCreate) -> SessionData:
        session_id = str(uuid.uuid4())
        now = self._now_iso()
        data = {
            "session_id": session_id,
            "user_id": payload.user_id,
            "conversation_context": [],
            "preferences": payload.preferences or {},
            "metadata": payload.metadata or {},
            "created_at": now,
            "updated_at": now,
            "expires_at": self._expires_iso(),
        }
        await self._save(data)
        return SessionData(**data)

    async def get_session(self, session_id: str) -> SessionData:
        data = await self._get_raw(session_id)
        if data is None:
            raise KeyError(f"Session '{session_id}' not found or expired")
        # Refresh TTL on access
        await self._save(data)
        data["expires_at"] = self._expires_iso()
        return SessionData(**data)

    async def update_session(self, session_id: str, payload: SessionUpdate) -> SessionData:
        data = await self._get_raw(session_id)
        if data is None:
            raise KeyError(f"Session '{session_id}' not found or expired")

        if payload.conversation_context is not None:
            # Append new messages; keep last 50 turns to avoid bloat
            existing: list = data.get("conversation_context", [])
            existing.extend(payload.conversation_context)
            data["conversation_context"] = existing[-50:]

        if payload.preferences is not None:
            data["preferences"].update(payload.preferences)

        if payload.metadata is not None:
            data["metadata"].update(payload.metadata)

        data["updated_at"] = self._now_iso()
        data["expires_at"] = self._expires_iso()
        await self._save(data)
        return SessionData(**data)

    async def delete_session(self, session_id: str) -> bool:
        if not self.redis:
            raise RuntimeError("Redis unavailable")
        deleted = await self.redis.delete(self._session_key(session_id))
        return deleted > 0
