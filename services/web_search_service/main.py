import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import WebSearchService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Web Search Service starting...")
    app.state.service = WebSearchService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Web Search Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "web_search_service", "port": 8077}
