import os
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logger = logging.getLogger("conversation_storage_service")

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongodb:27017")
MONGO_DB = os.getenv("MONGO_DB_NAME", "medbot")
COLLECTION = "conversations"


async def get_db():
    client = AsyncIOMotorClient(MONGO_URL)
    return client[MONGO_DB]


def _serialize(doc: dict) -> dict:
    """Convert MongoDB _id to string id."""
    if doc and "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


async def create_conversation(session_id: str, user_id: Optional[str], metadata: Optional[dict]) -> dict:
    db = await get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "session_id": session_id,
        "user_id": user_id,
        "metadata": metadata or {},
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }
    result = await db[COLLECTION].insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    logger.info("Created conversation id=%s session=%s", doc["id"], session_id)
    return doc


async def get_conversation(conversation_id: str) -> Optional[dict]:
    db = await get_db()
    try:
        oid = ObjectId(conversation_id)
    except Exception:
        return None
    doc = await db[COLLECTION].find_one({"_id": oid})
    if doc:
        return _serialize(doc)
    return None


async def add_message(conversation_id: str, message: dict) -> Optional[dict]:
    """Append a message object to the messages array of an existing conversation."""
    db = await get_db()
    try:
        oid = ObjectId(conversation_id)
    except Exception:
        return None

    message.setdefault("timestamp", datetime.now(timezone.utc))

    result = await db[COLLECTION].update_one(
        {"_id": oid},
        {
            "$push": {"messages": message},
            "$set": {"updated_at": datetime.now(timezone.utc)},
        },
    )
    if result.matched_count == 0:
        return None
    return await get_conversation(conversation_id)


async def get_by_session(session_id: str) -> List[dict]:
    db = await get_db()
    cursor = (
        db[COLLECTION]
        .find({"session_id": session_id})
        .sort("created_at", -1)
    )
    results = []
    async for doc in cursor:
        results.append(_serialize(doc))
    return results


async def delete_conversation(conversation_id: str) -> bool:
    db = await get_db()
    try:
        oid = ObjectId(conversation_id)
    except Exception:
        return False
    result = await db[COLLECTION].delete_one({"_id": oid})
    return result.deleted_count == 1


async def list_conversations(limit: int = 50, skip: int = 0) -> List[dict]:
    db = await get_db()
    cursor = (
        db[COLLECTION]
        .find({}, {"messages": 0})  # exclude messages for listing
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
    )
    results = []
    async for doc in cursor:
        results.append(_serialize(doc))
    return results
