"""
Reasoning Model Service - Business logic for medical reasoning using Ollama.
Wraps ollama_router_service with medical-domain system prompts.
"""
import httpx
from typing import Optional, List, Dict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_router_url: str = "http://ollama_router_service:8050"
    request_timeout: int = 120

    class Config:
        env_prefix = "REASONING_"


settings = Settings()

MEDICAL_SYSTEM_PROMPT = """You are a highly skilled medical AI assistant with expertise in clinical reasoning,
diagnosis, and treatment planning. Your role is to assist healthcare professionals and patients by:

1. Providing evidence-based medical information
2. Helping reason through differential diagnoses
3. Identifying potential red flags and emergency situations
4. Recommending appropriate next steps (tests, referrals, treatments)
5. Explaining complex medical concepts in clear language

IMPORTANT GUIDELINES:
- Always recommend consulting a qualified healthcare professional for personal medical advice
- Clearly state uncertainty when information is incomplete or ambiguous
- Prioritize patient safety above all else
- Flag potential drug interactions, contraindications, and allergies
- Use clinical reasoning frameworks (e.g., SOAP notes, differential diagnosis)
- Reference established medical guidelines when applicable (WHO, CDC, NICE, etc.)

You should be thorough, accurate, and compassionate in your responses."""


def build_medical_context_prompt(
    patient_context: Optional[Dict] = None,
    extra_context: Optional[str] = None,
) -> str:
    """Build an enriched system prompt with patient-specific context."""
    prompt = MEDICAL_SYSTEM_PROMPT

    if patient_context:
        context_parts = ["\n\nPATIENT CONTEXT:"]
        if patient_context.get("age"):
            context_parts.append(f"- Age: {patient_context['age']}")
        if patient_context.get("gender"):
            context_parts.append(f"- Gender: {patient_context['gender']}")
        if patient_context.get("medical_history"):
            context_parts.append(f"- Medical History: {patient_context['medical_history']}")
        if patient_context.get("current_medications"):
            context_parts.append(f"- Current Medications: {patient_context['current_medications']}")
        if patient_context.get("allergies"):
            context_parts.append(f"- Known Allergies: {patient_context['allergies']}")
        prompt += "\n".join(context_parts)

    if extra_context:
        prompt += f"\n\nADDITIONAL CONTEXT:\n{extra_context}"

    return prompt


async def generate_reasoning(
    prompt: str,
    patient_context: Optional[Dict] = None,
    extra_context: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> dict:
    """Generate a medical reasoning response via ollama_router_service."""
    system_prompt = build_medical_context_prompt(patient_context, extra_context)

    payload = {
        "prompt": prompt,
        "task_type": "reasoning",
        "system_prompt": system_prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.ollama_router_url}/api/v1/model/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "response": data.get("response", ""),
        "model": data.get("model", ""),
        "task_type": "medical_reasoning",
        "prompt_eval_count": data.get("prompt_eval_count", 0),
        "eval_count": data.get("eval_count", 0),
        "system_context_used": bool(patient_context or extra_context),
    }


async def chat_reasoning(
    messages: List[Dict[str, str]],
    patient_context: Optional[Dict] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> dict:
    """Multi-turn chat for medical reasoning. Converts history to a single prompt."""
    system_prompt = build_medical_context_prompt(patient_context)

    # Build conversation string from history
    conversation = []
    for msg in messages:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        conversation.append(f"{role}: {content}")

    full_prompt = "\n".join(conversation)
    if not full_prompt.endswith("Assistant:"):
        full_prompt += "\nAssistant:"

    payload = {
        "prompt": full_prompt,
        "task_type": "reasoning",
        "system_prompt": system_prompt,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.ollama_router_url}/api/v1/model/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return {
        "response": data.get("response", "").strip(),
        "model": data.get("model", ""),
        "task_type": "medical_chat",
        "turns": len(messages),
        "eval_count": data.get("eval_count", 0),
    }
