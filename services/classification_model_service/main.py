import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Classification Model Service starting...")
    yield
    logger.info("Classification Model Service shutting down.")


app = FastAPI(
    title="MEDBOT Classification Model Service",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "classification_model_service", "port": 8057}
