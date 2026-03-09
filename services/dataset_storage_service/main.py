from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dataset_storage_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Dataset Storage Service starting")
    yield
    logger.info("Dataset Storage Service shutting down")


app = FastAPI(
    title="MEDBOT Dataset Storage Service",
    version="1.0.0",
    lifespan=lifespan,
    description="Stores and exports training datasets for MEDBOT fine-tuning pipelines",
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
    return {"status": "ok", "service": "dataset_storage_service", "port": 8041}
