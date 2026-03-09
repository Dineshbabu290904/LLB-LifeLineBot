from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("logging_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Logging Service starting")
    yield
    logger.info("Logging Service shutting down")


app = FastAPI(
    title="MEDBOT Logging Service",
    version="1.0.0",
    lifespan=lifespan,
    description="Centralised log ingestion and retrieval for all MEDBOT services",
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
    return {"status": "ok", "service": "logging_service", "port": 8091}
