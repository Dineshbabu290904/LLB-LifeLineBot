import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import SymptomExtractionAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Symptom Extraction Agent starting...")
    app.state.service = SymptomExtractionAgent()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Symptom Extraction Agent", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "symptom_extraction_agent", "port": 8076}
