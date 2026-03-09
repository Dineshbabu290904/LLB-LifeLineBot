"""
Ollama Router Service - API route definitions.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from service import generate_text, generate_embeddings, analyze_vision, list_models

router = APIRouter(prefix="/api/v1/model", tags=["model"])


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="The input prompt for text generation")
    task_type: Optional[str] = Field(
        None,
        description="Task type: reasoning, vision, embedding, classification",
    )
    model: Optional[str] = Field(None, description="Override model selection")
    system_prompt: Optional[str] = Field(None, description="System-level instructions")
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=1, le=8192)


class EmbedRequest(BaseModel):
    text: str = Field(..., description="Text to embed")
    model: Optional[str] = Field(None, description="Override embedding model")


class VisionRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image")
    prompt: str = Field(
        "Describe this medical image in detail.",
        description="Vision analysis prompt",
    )
    model: Optional[str] = Field(None, description="Override vision model")


@router.post("/generate")
async def route_generate(request: GenerateRequest):
    """Generate text by routing to the appropriate Ollama model based on task_type."""
    try:
        result = await generate_text(
            prompt=request.prompt,
            task_type=request.task_type,
            model_override=request.model,
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Ollama error: {str(e)}")


@router.post("/embed")
async def route_embed(request: EmbedRequest):
    """Generate embeddings for the provided text."""
    try:
        result = await generate_embeddings(
            text=request.text,
            model_override=request.model,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Embedding error: {str(e)}")


@router.post("/vision")
async def route_vision(request: VisionRequest):
    """Analyze an image using the llava vision model."""
    try:
        result = await analyze_vision(
            image_base64=request.image_base64,
            prompt=request.prompt,
            model_override=request.model,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vision error: {str(e)}")


@router.get("/models")
async def route_list_models():
    """List all available Ollama models and the task routing configuration."""
    try:
        return await list_models()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not reach Ollama: {str(e)}")
