from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("config_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Config Service starting on port 8090")
    yield
    logger.info("Config Service shutting down")


app = FastAPI(title="MEDBOT Config Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "config_service", "port": 8090}
