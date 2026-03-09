import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from router import router
from service import RateLimitService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Rate limit service starting up...")
    svc = RateLimitService()
    await svc.init_redis()
    app.state.rate_limit_service = svc
    logger.info("Rate limit service ready.")
    yield
    logger.info("Rate limit service shutting down...")
    await app.state.rate_limit_service.close()
    logger.info("Rate limit service stopped.")


app = FastAPI(
    title="MEDBOT Rate Limit Service",
    description="Sliding-window rate limiter: 100 requests per 60 seconds per client",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "rate_limit_service", "port": 8003}
