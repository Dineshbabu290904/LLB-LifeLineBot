"""
Embedding Model Service - Main application entry point.
Generates text embeddings using sentence-transformers all-MiniLM-L6-v2 (384 dims).
Port: 8052
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router

app = FastAPI(
    title="Embedding Model Service",
    description="Generates normalized 384-dimensional text embeddings using all-MiniLM-L6-v2 for semantic search and RAG.",
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
    return {"status": "healthy", "service": "embedding_model_service", "port": 8052}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8052, reload=True)
