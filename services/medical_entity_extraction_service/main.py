from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router

app = FastAPI(
    title="Medical Entity Extraction Service",
    description="NER service for extracting medical entities: symptoms, medications, conditions, procedures, anatomy, measurements.",
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
    return {"status": "healthy", "service": "medical_entity_extraction_service", "port": 8070}


@app.get("/")
async def root():
    return {
        "service": "medical_entity_extraction_service",
        "version": "1.0.0",
        "endpoints": ["/api/v1/entities/extract", "/health"],
    }
