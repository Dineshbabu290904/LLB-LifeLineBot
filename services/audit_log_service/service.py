import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logger = logging.getLogger("audit_log_service")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "medbot")
COLLECTION = "audit_logs"


async def get_db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[MONGO_DB]


def _hash(value: Optional[str]) -> Optional[str]:
    """SHA-256 hex digest of a string value, or None if not provided."""
    if value is None:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _serialize(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


async def record_audit_event(
    session_id: str,
    agent_name: str,
    action: str,
    input_data: Optional[str],
    output_data: Optional[str],
    user_id: Optional[str],
    extra: Optional[dict],
) -> dict:
    """
    Persist an immutable audit event.

    input_data and output_data are stored only as SHA-256 hashes to
    protect PII while enabling integrity verification.
    """
    db = await get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "session_id": session_id,
        "agent_name": agent_name,
        "action": action,
        "input_hash": _hash(input_data),
        "output_hash": _hash(output_data),
        "user_id": user_id,
        "extra": extra or {},
        "timestamp": now,
        # No updates allowed after insertion — this makes the record immutable
    }
    result = await db[COLLECTION].insert_one(doc)
    audit_id = str(result.inserted_id)
    logger.info(
        "Audit event id=%s session=%s agent=%s action=%s",
        audit_id, session_id, agent_name, action,
    )
    doc["id"] = audit_id
    doc.pop("_id", None)
    return doc


async def list_audit_events(
    session_id: Optional[str],
    agent_name: Optional[str],
    action: Optional[str],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
    limit: int,
    skip: int,
) -> List[dict]:
    db = await get_db()
    query: dict = {}
    if session_id:
        query["session_id"] = session_id
    if agent_name:
        query["agent_name"] = agent_name
    if action:
        query["action"] = action
    if from_date or to_date:
        ts_filter: dict = {}
        if from_date:
            ts_filter["$gte"] = from_date
        if to_date:
            ts_filter["$lte"] = to_date
        query["timestamp"] = ts_filter

    cursor = (
        db[COLLECTION]
        .find(query)
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
    )
    results = []
    async for doc in cursor:
        results.append(_serialize(doc))
    return results


async def count_audit_events(
    session_id: Optional[str],
    agent_name: Optional[str],
    action: Optional[str],
    from_date: Optional[datetime],
    to_date: Optional[datetime],
) -> int:
    db = await get_db()
    query: dict = {}
    if session_id:
        query["session_id"] = session_id
    if agent_name:
        query["agent_name"] = agent_name
    if action:
        query["action"] = action
    if from_date or to_date:
        ts_filter: dict = {}
        if from_date:
            ts_filter["$gte"] = from_date
        if to_date:
            ts_filter["$lte"] = to_date
        query["timestamp"] = ts_filter
    return await db[COLLECTION].count_documents(query)


async def get_audit_event(audit_id: str) -> Optional[dict]:
    db = await get_db()
    try:
        oid = ObjectId(audit_id)
    except Exception:
        return None
    doc = await db[COLLECTION].find_one({"_id": oid})
    if doc:
        return _serialize(doc)
    return None
