import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from router import router
from service import DoctorRecommendationAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Doctor Recommendation Agent starting...")
    app.state.service = DoctorRecommendationAgent()
    await app.state.service.startup()
    yield
    await app.state.service.shutdown()

app = FastAPI(title="MEDBOT Doctor Recommendation Agent", version="1.0.0", lifespan=lifespan)
app.include_router(router)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "doctor_recommendation_agent", "port": 8081}
