import aioredis
import json
from typing import Callable, Any, Dict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MedBotEvent(str, Enum):
    NEW_DOCUMENT = "medbot:new_document"
    TRAINING_TRIGGERED = "medbot:training_triggered"
    EVALUATION_COMPLETE = "medbot:evaluation_complete"
    MODEL_UPDATED = "medbot:model_updated"
    EMERGENCY_DETECTED = "medbot:emergency_detected"
    DATASET_READY = "medbot:dataset_ready"
    BENCHMARK_COMPLETE = "medbot:benchmark_complete"


class RedisPubSub:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._publisher: aioredis.Redis = None
        self._subscriber: aioredis.Redis = None

    async def connect(self):
        self._publisher = await aioredis.from_url(
            self.redis_url, encoding="utf-8", decode_responses=True
        )
        self._subscriber = await aioredis.from_url(
            self.redis_url, encoding="utf-8", decode_responses=True
        )
        logger.info("Redis PubSub connected")

    async def publish(self, event: MedBotEvent, data: Dict[str, Any]) -> int:
        if not self._publisher:
            await self.connect()
        message = json.dumps(data)
        count = await self._publisher.publish(event.value, message)
        logger.debug(f"Published event {event.value} to {count} subscribers")
        return count

    async def subscribe(self, event: MedBotEvent, handler: Callable):
        if not self._subscriber:
            await self.connect()
        pubsub = self._subscriber.pubsub()
        await pubsub.subscribe(event.value)
        logger.info(f"Subscribed to event: {event.value}")

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await handler(data)
                except Exception as e:
                    logger.error(f"Error processing event {event.value}: {e}")

    async def close(self):
        if self._publisher:
            await self._publisher.close()
        if self._subscriber:
            await self._subscriber.close()
