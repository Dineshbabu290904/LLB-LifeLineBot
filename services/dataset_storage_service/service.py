import os
import json
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logger = logging.getLogger("dataset_storage_service")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "medbot")
COLLECTION = "datasets"


async def get_db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[MONGO_DB]


def _serialize(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


async def store_dataset(
    source: str,
    prompt: str,
    response: str,
    quality_score: float,
    triage_label: Optional[str],
    metadata: Optional[dict],
) -> dict:
    db = await get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "source": source,
        "prompt": prompt,
        "response": response,
        "quality_score": quality_score,
        "triage_label": triage_label,
        "metadata": metadata or {},
        "created_at": now,
        "updated_at": now,
    }
    result = await db[COLLECTION].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    logger.info("Stored dataset record id=%s source=%s quality=%.2f", doc["id"], source, quality_score)
    return doc


async def list_datasets(
    min_quality: Optional[float],
    source: Optional[str],
    triage_label: Optional[str],
    limit: int,
    skip: int,
) -> List[dict]:
    db = await get_db()
    query: dict = {}
    if min_quality is not None:
        query["quality_score"] = {"$gte": min_quality}
    if source:
        query["source"] = source
    if triage_label:
        query["triage_label"] = triage_label

    cursor = (
        db[COLLECTION]
        .find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    results = []
    async for doc in cursor:
        results.append(_serialize(doc))
    return results


async def get_dataset(dataset_id: str) -> Optional[dict]:
    db = await get_db()
    try:
        oid = ObjectId(dataset_id)
    except Exception:
        return None
    doc = await db[COLLECTION].find_one({"_id": oid})
    if doc:
        return _serialize(doc)
    return None


async def export_as_jsonl(
    min_quality: Optional[float],
    source: Optional[str],
    triage_label: Optional[str],
    limit: int,
) -> str:
    """
    Return dataset records serialised as JSONL.
    Each line is: {"prompt": "...", "response": "...", "triage_label": "...", "quality_score": ...}
    """
    db = await get_db()
    query: dict = {}
    if min_quality is not None:
        query["quality_score"] = {"$gte": min_quality}
    if source:
        query["source"] = source
    if triage_label:
        query["triage_label"] = triage_label

    cursor = (
        db[COLLECTION]
        .find(query, {"prompt": 1, "response": 1, "triage_label": 1, "quality_score": 1})
        .sort("quality_score", -1)
        .limit(limit)
    )

    lines = []
    async for doc in cursor:
        doc.pop("_id", None)
        lines.append(json.dumps(doc, default=str))

    return "\n".join(lines)


async def count_datasets(
    min_quality: Optional[float],
    source: Optional[str],
    triage_label: Optional[str],
) -> int:
    db = await get_db()
    query: dict = {}
    if min_quality is not None:
        query["quality_score"] = {"$gte": min_quality}
    if source:
        query["source"] = source
    if triage_label:
        query["triage_label"] = triage_label
    return await db[COLLECTION].count_documents(query)
