import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import AgentControllerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Agent Controller starting...")
    app.state.service = AgentControllerService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()


app = FastAPI(title="MEDBOT Agent Controller", version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent_controller", "port": 8005}
