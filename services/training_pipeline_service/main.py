import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import TrainingPipelineService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Training Pipeline Service starting...")
    app.state.service = TrainingPipelineService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Training Pipeline Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "training_pipeline_service", "port": 8111}
