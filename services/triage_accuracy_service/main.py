from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("triage_accuracy_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Triage Accuracy Service starting on port 8101")
    yield
    logger.info("Triage Accuracy Service shutting down")


app = FastAPI(
    title="MEDBOT Triage Accuracy Service",
    version="1.0.0",
    description="Validates triage decisions against symptom analysis",
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
    return {"status": "ok", "service": "triage_accuracy_service", "port": 8101}
