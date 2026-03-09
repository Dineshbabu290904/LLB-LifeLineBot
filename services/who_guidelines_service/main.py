import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import WHOGuidelinesService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("WHO Guidelines Service starting...")
    app.state.service = WHOGuidelinesService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT WHO Guidelines Service", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "who_guidelines_service", "port": 8078}
