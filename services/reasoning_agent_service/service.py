"""Reasoning Agent Service - medical clinical reasoning."""
import logging
import httpx
import os
from typing import List, Optional

logger = logging.getLogger(__name__)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")

class ReasoningAgentService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def startup(self):
        self._client = httpx.AsyncClient(timeout=120.0)
        logger.info("Reasoning Agent Service ready.")

    async def shutdown(self):
        if self._client:
            await self._client.aclose()

    async def _generate(self, prompt: str) -> str:
        try:
            resp = await self._client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": "llama3.2:3b", "prompt": prompt, "stream": False}
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            return f"Reasoning unavailable: {e}"

    async def reason(self, question: str, patient_context: Optional[str] = None) -> dict:
        context_section = f"\nPatient Context: {patient_context}" if patient_context else ""
        prompt = f"""You are a clinical reasoning AI assistant. Analyze the following medical question step by step.{context_section}

Medical Question: {question}

Reasoning Steps:
1. Identify the key medical concepts
2. Consider relevant clinical factors
3. Apply evidence-based guidelines
4. Formulate a reasoned response

Clinical Reasoning:"""
        reasoning = await self._generate(prompt)
        return {"question": question, "reasoning": reasoning, "patient_context": patient_context}

    async def differential(self, symptoms: List[str], patient_context: Optional[str] = None) -> dict:
        symptoms_str = ", ".join(symptoms)
        context_section = f"\nPatient Context: {patient_context}" if patient_context else ""
        prompt = f"""You are a clinical AI. Generate a differential diagnosis for these symptoms.{context_section}

Symptoms: {symptoms_str}

Differential Diagnosis (list most likely to least likely with brief reasoning):"""
        diagnosis = await self._generate(prompt)
        return {"symptoms": symptoms, "differential_diagnosis": diagnosis, "disclaimer": "This is AI-generated and not a substitute for professional medical advice."}
