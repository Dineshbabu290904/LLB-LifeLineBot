from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("medical_consistency_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Medical Consistency Service starting on port 8102")
    yield
    logger.info("Medical Consistency Service shutting down")


app = FastAPI(
    title="MEDBOT Medical Consistency Service",
    version="1.0.0",
    description="Cross-checks medical responses against retrieved source documents",
    lifespan=lifespan,
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
    return {"status": "ok", "service": "medical_consistency_service", "port": 8102}
