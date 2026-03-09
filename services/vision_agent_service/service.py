"""Vision Agent Service - processes medical images using vision models."""
import logging
import base64
import httpx
import os
from typing import Optional

logger = logging.getLogger(__name__)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

class VisionAgentService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=120.0)
        logger.info("Vision Agent Service ready.")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def analyze(self, image_data: str, image_type: str = "xray", query: str = "Describe what you see in this medical image.") -> dict:
        try:
            resp = await self._client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": "llava:7b",
                    "prompt": f"You are a medical imaging AI assistant. {query}",
                    "images": [image_data],
                    "stream": False
                }
            )
            resp.raise_for_status()
            analysis = resp.json().get("response", "")
        except Exception as e:
            logger.error("Vision model error: %s", e)
            analysis = f"Image analysis unavailable: {e}"

        return {
            "image_type": image_type,
            "query": query,
            "analysis": analysis,
            "disclaimer": "This AI analysis is not a substitute for professional radiological interpretation.",
        }

    async def describe(self, image_data: str, findings_type: str = "general") -> dict:
        query_map = {
            "general": "Provide a general description of findings in this medical image.",
            "xray": "Describe the key findings in this chest X-ray, including lung fields, cardiac silhouette, and any abnormalities.",
            "pathology": "Describe the histological findings visible in this pathology slide.",
        }
        query = query_map.get(findings_type, query_map["general"])
        result = await self.analyze(image_data, findings_type, query)
        return {**result, "findings_type": findings_type}
