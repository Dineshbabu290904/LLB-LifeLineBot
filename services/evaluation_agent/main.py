import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import EvaluationAgentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Evaluation Agent starting...")
    app.state.service = EvaluationAgentService()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Evaluation Agent", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "evaluation_agent", "port": 8029}
