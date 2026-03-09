from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hallucination_detection_agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Hallucination Detection Agent starting on port 8104")
    yield
    logger.info("Hallucination Detection Agent shutting down")


app = FastAPI(
    title="MEDBOT Hallucination Detection Agent",
    version="1.0.0",
    description="Detects hallucinated claims in AI-generated medical responses",
    lifespan=lifespan,
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
    return {"status": "ok", "service": "hallucination_detection_agent", "port": 8104}
