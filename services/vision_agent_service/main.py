import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import VisionAgentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Vision Agent Service starting...")
    app.state.service = VisionAgentService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Vision Agent Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "vision_agent_service", "port": 8023}
