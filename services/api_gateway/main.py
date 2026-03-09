import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import GatewayService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API Gateway starting...")
    app.state.gateway_service = GatewayService()
    await app.state.gateway_service.start()
    yield
    await app.state.gateway_service.stop()


app = FastAPI(title="MEDBOT API Gateway", version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "api_gateway", "port": 8000}
