import logging
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from router import router
from service import AuthService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and teardown application resources."""
    logger.info("Auth service starting up...")
    app.state.auth_service = AuthService()
    await app.state.auth_service.init_db()
    logger.info("Auth service ready.")
    yield
    logger.info("Auth service shutting down...")
    if app.state.auth_service.pool:
        await app.state.auth_service.pool.close()
    logger.info("Auth service stopped.")


app = FastAPI(
    title="MEDBOT Auth Service",
    description="JWT authentication and user management service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth_service", "port": 8001}
