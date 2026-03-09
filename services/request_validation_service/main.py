import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from router import router
from service import ValidationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Request validation service starting up...")
    app.state.validation_service = ValidationService()
    logger.info("Request validation service ready.")
    yield
    logger.info("Request validation service stopped.")


app = FastAPI(
    title="MEDBOT Request Validation Service",
    description=(
        "Input validation and sanitization: query length, prompt injection, "
        "PII redaction, image format and size checks."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "request_validation_service",
        "port": 8004,
    }
