import os
from datetime import datetime, timezone
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger("logging_service")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "medbot")

VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class LogEntry(BaseModel):
    service: str
    level: str
    message: str
    timestamp: Optional[datetime] = None
    extra: Optional[dict] = None


class LogRecord(LogEntry):
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


async def get_db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[MONGO_DB]


async def store_log(entry: LogEntry) -> dict:
    db = await get_db()
    level = entry.level.upper()
    if level not in VALID_LEVELS:
        level = "INFO"

    doc = {
        "service": entry.service,
        "level": level,
        "message": entry.message,
        "timestamp": entry.timestamp or datetime.now(timezone.utc),
        "extra": entry.extra or {},
    }

    result = await db["logs"].insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    logger.debug("Stored log entry id=%s service=%s level=%s", doc["_id"], entry.service, level)
    return {"id": doc["_id"], "status": "stored"}


async def query_logs(
    service: Optional[str],
    level: Optional[str],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    limit: int,
    skip: int,
) -> List[dict]:
    db = await get_db()
    query: dict = {}

    if service:
        query["service"] = service
    if level:
        query["level"] = level.upper()
    if from_date or to_date:
        ts_filter: dict = {}
        if from_date:
            ts_filter["$gte"] = from_date
        if to_date:
            ts_filter["$lte"] = to_date
        query["timestamp"] = ts_filter

    cursor = (
        db["logs"]
        .find(query, {"_id": 1, "service": 1, "level": 1, "message": 1, "timestamp": 1, "extra": 1})
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )

    results = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        results.append(doc)

    return results


async def count_logs(
    service: Optional[str],
    level: Optional[str],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> int:
    db = await get_db()
    query: dict = {}
    if service:
        query["service"] = service
    if level:
        query["level"] = level.upper()
    if from_date or to_date:
        ts_filter: dict = {}
        if from_date:
            ts_filter["$gte"] = from_date
        if to_date:
            ts_filter["$lte"] = to_date
        query["timestamp"] = ts_filter

    return await db["logs"].count_documents(query)
