from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monitoring_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Monitoring Service starting")
    yield
    logger.info("Monitoring Service shutting down")


app = FastAPI(
    title="MEDBOT Monitoring Service",
    version="1.0.0",
    lifespan=lifespan,
    description="Polls all MEDBOT service /health endpoints and aggregates status",
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
    return {"status": "ok", "service": "monitoring_service", "port": 8092}
