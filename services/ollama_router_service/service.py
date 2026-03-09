"""
Ollama Router Service - Business logic for routing AI requests to Ollama models.
"""
import httpx
import base64
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_base_url: str = "http://ollama:11434"
    request_timeout: int = 120

    class Config:
        env_prefix = "OLLAMA_ROUTER_"


settings = Settings()

# Task type to model mapping
TASK_MODEL_MAP = {
    "reasoning": "llama3.2:latest",
    "vision": "llava:latest",
    "embedding": "nomic-embed-text",
    "classification": "phi3:mini",
    "default": "llama3.2:latest",
}


def resolve_model(task_type: Optional[str], model_override: Optional[str]) -> str:
    """Resolve the Ollama model to use based on task type or explicit override."""
    if model_override:
        return model_override
    if task_type and task_type in TASK_MODEL_MAP:
        return TASK_MODEL_MAP[task_type]
    return TASK_MODEL_MAP["default"]


async def generate_text(
    prompt: str,
    task_type: Optional[str] = None,
    model_override: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    stream: bool = False,
) -> dict:
    """Generate text using Ollama."""
    model = resolve_model(task_type, model_override)
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "model": model,
        "task_type": task_type or "default",
        "response": data.get("response", ""),
        "done": data.get("done", True),
        "prompt_eval_count": data.get("prompt_eval_count", 0),
        "eval_count": data.get("eval_count", 0),
    }


async def generate_embeddings(text: str, model_override: Optional[str] = None) -> dict:
    """Generate embeddings using Ollama nomic-embed-text model."""
    model = model_override or TASK_MODEL_MAP["embedding"]
    payload = {"model": model, "prompt": text}

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    embedding = data.get("embedding", [])
    return {
        "model": model,
        "embedding": embedding,
        "dimensions": len(embedding),
    }


async def analyze_vision(
    image_base64: str,
    prompt: str = "Describe this medical image in detail.",
    model_override: Optional[str] = None,
) -> dict:
    """Analyze an image using Ollama llava model."""
    model = model_override or TASK_MODEL_MAP["vision"]
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_base64],
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "model": model,
        "task_type": "vision",
        "response": data.get("response", ""),
        "done": data.get("done", True),
    }


async def list_models() -> dict:
    """List all models available in Ollama."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{settings.ollama_base_url}/api/tags")
        response.raise_for_status()
        data = response.json()

    models = data.get("models", [])
    return {
        "models": [
            {
                "name": m.get("name"),
                "size": m.get("size"),
                "modified_at": m.get("modified_at"),
                "digest": m.get("digest", "")[:12],
            }
            for m in models
        ],
        "count": len(models),
        "task_routing": TASK_MODEL_MAP,
    }
