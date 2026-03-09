import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from router import router
from service import SessionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Session service starting up...")
    svc = SessionService()
    await svc.init_redis()
    app.state.session_service = svc
    logger.info("Session service ready.")
    yield
    logger.info("Session service shutting down...")
    await app.state.session_service.close()
    logger.info("Session service stopped.")


app = FastAPI(
    title="MEDBOT Session Service",
    description="Redis-backed session management with TTL and conversation context",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "session_service", "port": 8002}
