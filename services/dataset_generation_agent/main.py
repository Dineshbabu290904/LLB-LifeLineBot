import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import DatasetGenerationAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Dataset Generation Agent starting...")
    app.state.service = DatasetGenerationAgent()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Dataset Generation Agent", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "dataset_generation_agent", "port": 8030}
