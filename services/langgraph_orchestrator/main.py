from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from router import router
from graph import get_compiled_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("langgraph_orchestrator")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LangGraph Orchestrator starting — compiling graph...")
    # Pre-compile the graph at startup
    graph = get_compiled_graph()
    logger.info("MedBot pipeline graph compiled and ready")
    yield
    logger.info("LangGraph Orchestrator shutting down")


app = FastAPI(
    title="MEDBOT LangGraph Orchestrator",
    description="Autonomous multi-agent medical pipeline powered by LangGraph",
    version="1.0.0",
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
    return {
        "status": "ok",
        "service": "langgraph_orchestrator",
        "port": 8010,
        "pipeline": "compiled",
    }
