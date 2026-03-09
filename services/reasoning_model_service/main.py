"""
Reasoning Model Service - Main application entry point.
Wraps Ollama with medical reasoning context for clinical AI support.
Port: 8051
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router

app = FastAPI(
    title="Reasoning Model Service",
    description="Medical reasoning AI powered by llama3.2 via Ollama. Provides structured clinical reasoning with patient context.",
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
    return {"status": "healthy", "service": "reasoning_model_service", "port": 8051}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8051, reload=True)
