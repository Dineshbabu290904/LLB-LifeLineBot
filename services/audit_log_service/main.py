from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("audit_log_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Audit Log Service starting")
    yield
    logger.info("Audit Log Service shutting down")


app = FastAPI(
    title="MEDBOT Audit Log Service",
    version="1.0.0",
    lifespan=lifespan,
    description="Immutable audit trail for all MEDBOT agent actions and decisions",
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
    return {"status": "ok", "service": "audit_log_service", "port": 8043}
