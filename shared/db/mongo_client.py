from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None


async def get_mongo_client(mongo_url: str) -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        logger.info("MongoDB client initialized")
    return _client


async def get_mongo_db(mongo_url: str, db_name: str) -> AsyncIOMotorDatabase:
    client = await get_mongo_client(mongo_url)
    return client[db_name]


async def close_mongo_client():
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB client closed")


async def create_indexes(db: AsyncIOMotorDatabase):
    """Create required indexes for all collections."""
    # conversations
    await db.conversations.create_index("session_id")
    await db.conversations.create_index("created_at")
    # datasets
    await db.datasets.create_index("conversation_id")
    await db.datasets.create_index("quality_score")
    await db.datasets.create_index("created_at")
    await db.datasets.create_index("is_validated")
    # knowledge_base
    await db.knowledge_base.create_index("source_url", unique=True)
    await db.knowledge_base.create_index("validated_at")
    # audit_logs
    await db.audit_logs.create_index("session_id")
    await db.audit_logs.create_index("created_at")
    # evaluation_reports
    await db.evaluation_reports.create_index("conversation_id")
    await db.evaluation_reports.create_index("requires_retraining")
    # model_registry
    await db.model_registry.create_index("version")
    await db.model_registry.create_index("created_at")
    logger.info("MongoDB indexes created")
