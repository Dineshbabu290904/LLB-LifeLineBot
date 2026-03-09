import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import DatasetLabelingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Dataset Labeling Model Service starting...")
    app.state.service = DatasetLabelingService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Dataset Labeling Model Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "dataset_labeling_model_service", "port": 8031}
