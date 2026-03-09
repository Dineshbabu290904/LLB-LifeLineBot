import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import ContextBuilderService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Context Builder Service starting...")
    app.state.service = ContextBuilderService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Context Builder Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "context_builder_service", "port": 8020}
