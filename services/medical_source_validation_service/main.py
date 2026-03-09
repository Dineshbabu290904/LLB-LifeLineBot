import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import MedicalSourceValidationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Medical Source Validation Service starting...")
    app.state.service = MedicalSourceValidationService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Medical Source Validation Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "medical_source_validation_service", "port": 8073}
