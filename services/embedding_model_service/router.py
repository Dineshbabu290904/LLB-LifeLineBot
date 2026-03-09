"""
Embedding Model Service - API route definitions.
"""
from typing import List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from service import embed_single, embed_batch, get_model_info

router = APIRouter(prefix="/api/v1/embeddings", tags=["embeddings"])


class EmbedRequest(BaseModel):
    text: str = Field(..., description="Text to embed", min_length=1)


class EmbedResponse(BaseModel):
    embedding: List[float]
    dimensions: int
    model: str
    text_preview: str


class BatchEmbedRequest(BaseModel):
    texts: List[str] = Field(..., description="List of texts to embed", min_length=1)


class BatchEmbedResponse(BaseModel):
    embeddings: List[List[float]]
    dimensions: int
    model: str
    count: int


@router.post("/generate", response_model=EmbedResponse)
async def generate_embedding(request: EmbedRequest):
    """
    Generate a normalized 384-dimensional embedding for a single text.
    The vector is L2-normalized, suitable for cosine similarity via dot product.
    """
    try:
        embedding = embed_single(request.text)
        info = get_model_info()
        return EmbedResponse(
            embedding=embedding,
            dimensions=len(embedding),
            model=info["model_name"],
            text_preview=request.text[:100] + ("..." if len(request.text) > 100 else ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")


@router.post("/batch", response_model=BatchEmbedResponse)
async def batch_generate_embeddings(request: BatchEmbedRequest):
    """
    Generate normalized embeddings for a batch of texts.
    More efficient than calling /generate individually for each text.
    """
    try:
        embeddings = embed_batch(request.texts)
        info = get_model_info()
        return BatchEmbedResponse(
            embeddings=embeddings,
            dimensions=len(embeddings[0]) if embeddings else 384,
            model=info["model_name"],
            count=len(embeddings),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch embedding failed: {str(e)}")


@router.get("/info")
async def model_info():
    """Return metadata about the embedding model."""
    return get_model_info()
