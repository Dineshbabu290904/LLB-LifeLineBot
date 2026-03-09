from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router

app = FastAPI(
    title="Severity Classification Service",
    description="Classifies symptom severity (mild/moderate/severe/critical) with numeric scoring using rule-based logic and LLM augmentation.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "severity_classification_service", "port": 8071}


@app.get("/")
async def root():
    return {
        "service": "severity_classification_service",
        "version": "1.0.0",
        "endpoints": ["/api/v1/severity/classify", "/api/v1/severity/score", "/health"],
    }
