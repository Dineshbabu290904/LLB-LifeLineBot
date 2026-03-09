import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
import aioredis

logger = logging.getLogger("metrics_service")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# In-memory store (also mirrored to Redis for persistence)
_metrics: dict = {
    "requests_count": 0,
    "errors": 0,
    "total_response_time_ms": 0.0,
    "response_time_samples": 0,
    "triage_distribution": {},   # triage_level -> count
    "by_service": {},            # service -> {requests, errors, total_response_time_ms}
    "last_reset": datetime.now(timezone.utc).isoformat(),
}

_redis: Optional[aioredis.Redis] = None
_REDIS_KEY = "medbot:metrics"
_persist_lock = asyncio.Lock()


async def init_redis() -> None:
    global _redis, _metrics
    try:
        _redis = await aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        stored = await _redis.get(_REDIS_KEY)
        if stored:
            loaded = json.loads(stored)
            _metrics.update(loaded)
            logger.info("Metrics restored from Redis")
        else:
            logger.info("No prior metrics found in Redis; starting fresh")
    except Exception as exc:
        logger.warning("Redis unavailable (%s); running in-memory only", exc)
        _redis = None


async def close_redis() -> None:
    global _redis
    if _redis:
        await _persist_to_redis()
        await _redis.close()
        _redis = None


async def _persist_to_redis() -> None:
    if _redis is None:
        return
    async with _persist_lock:
        try:
            await _redis.set(_REDIS_KEY, json.dumps(_metrics))
        except Exception as exc:
            logger.warning("Could not persist metrics to Redis: %s", exc)


async def record_metric(
    service: str,
    event_type: str,
    response_time_ms: Optional[float],
    triage_level: Optional[str],
    is_error: bool,
    extra: Optional[dict],
) -> dict:
    """
    Record a metric event.

    event_type values: request | error | triage
    """
    _metrics["requests_count"] += 1

    if is_error:
        _metrics["errors"] += 1

    if response_time_ms is not None:
        _metrics["total_response_time_ms"] += response_time_ms
        _metrics["response_time_samples"] += 1

    if triage_level:
        lvl = triage_level.lower()
        _metrics["triage_distribution"][lvl] = (
            _metrics["triage_distribution"].get(lvl, 0) + 1
        )

    svc = _metrics["by_service"].setdefault(
        service, {"requests": 0, "errors": 0, "total_response_time_ms": 0.0}
    )
    svc["requests"] += 1
    if is_error:
        svc["errors"] += 1
    if response_time_ms is not None:
        svc["total_response_time_ms"] += response_time_ms

    await _persist_to_redis()

    return {
        "status": "recorded",
        "event_type": event_type,
        "service": service,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _avg_response_time() -> Optional[float]:
    samples = _metrics["response_time_samples"]
    if samples == 0:
        return None
    return round(_metrics["total_response_time_ms"] / samples, 2)


async def get_summary() -> dict:
    """Return a snapshot of all collected metrics."""
    error_rate = 0.0
    total = _metrics["requests_count"]
    if total > 0:
        error_rate = round(_metrics["errors"] / total * 100, 2)

    per_service_summary = {}
    for svc, data in _metrics["by_service"].items():
        avg_rt = None
        if data["requests"] > 0 and data["total_response_time_ms"] > 0:
            avg_rt = round(data["total_response_time_ms"] / data["requests"], 2)
        per_service_summary[svc] = {
            "requests": data["requests"],
            "errors": data["errors"],
            "error_rate_pct": round(data["errors"] / data["requests"] * 100, 2) if data["requests"] else 0.0,
            "avg_response_time_ms": avg_rt,
        }

    return {
        "requests_count": _metrics["requests_count"],
        "errors": _metrics["errors"],
        "error_rate_pct": error_rate,
        "avg_response_time_ms": _avg_response_time(),
        "triage_distribution": dict(_metrics["triage_distribution"]),
        "by_service": per_service_summary,
        "last_reset": _metrics["last_reset"],
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
    }


async def reset_metrics() -> dict:
    """Reset all in-memory (and Redis) metrics to zero."""
    global _metrics
    _metrics = {
        "requests_count": 0,
        "errors": 0,
        "total_response_time_ms": 0.0,
        "response_time_samples": 0,
        "triage_distribution": {},
        "by_service": {},
        "last_reset": datetime.now(timezone.utc).isoformat(),
    }
    await _persist_to_redis()
    return {"status": "reset", "timestamp": _metrics["last_reset"]}
