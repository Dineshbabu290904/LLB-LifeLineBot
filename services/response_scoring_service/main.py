import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import ResponseScoringService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Response Scoring Service starting...")
    app.state.service = ResponseScoringService()
    yield
    logger.info("Response Scoring Service shutting down.")


app = FastAPI(
    title="MEDBOT Response Scoring Service",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "response_scoring_service", "port": 8058}
