import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import VectorSearchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Vector Search Service starting...")
    app.state.service = VectorSearchService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Vector Search Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "vector_search_service", "port": 8056}
