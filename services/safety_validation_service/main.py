from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("safety_validation_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Safety Validation Service starting on port 8103")
    yield
    logger.info("Safety Validation Service shutting down")


app = FastAPI(
    title="MEDBOT Safety Validation Service",
    version="1.0.0",
    description="Medical safety compliance validation for AI-generated responses",
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
    return {"status": "ok", "service": "safety_validation_service", "port": 8103}
