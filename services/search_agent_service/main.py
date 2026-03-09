import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import SearchAgentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Search Agent Service starting...")
    app.state.service = SearchAgentService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Search Agent Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "search_agent_service", "port": 8028}
