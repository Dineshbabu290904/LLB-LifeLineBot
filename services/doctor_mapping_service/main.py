import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import DoctorMappingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Doctor Mapping Service starting...")
    app.state.service = DoctorMappingService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Doctor Mapping Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "doctor_mapping_service", "port": 8080}
