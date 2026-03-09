from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("conversation_storage_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Conversation Storage Service starting")
    yield
    logger.info("Conversation Storage Service shutting down")


app = FastAPI(
    title="MEDBOT Conversation Storage Service",
    version="1.0.0",
    lifespan=lifespan,
    description="CRUD persistence layer for MEDBOT conversation histories",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "conversation_storage_service", "port": 8040}
