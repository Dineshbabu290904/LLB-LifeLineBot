from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router
from service import init_redis, close_redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("metrics_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Metrics Service starting")
    await init_redis()
    yield
    await close_redis()
    logger.info("Metrics Service shutting down")


app = FastAPI(
    title="MEDBOT Metrics Service",
    version="1.0.0",
    lifespan=lifespan,
    description="Collects and summarises runtime metrics for the MEDBOT platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "metrics_service", "port": 8093}
