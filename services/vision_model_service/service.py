"""
Vision Model Service - Business logic for medical image analysis.
Uses OpenCV for preprocessing and routes to llava via ollama_router_service.
"""
import base64
import io
import httpx
import numpy as np
import cv2
from PIL import Image
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_router_url: str = "http://ollama_router_service:8050"
    request_timeout: int = 180

    class Config:
        env_prefix = "VISION_"


settings = Settings()


def decode_base64_image(image_base64: str) -> np.ndarray:
    """Decode a base64-encoded image string to an OpenCV numpy array."""
    # Strip data URI prefix if present (e.g. "data:image/png;base64,...")
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]
    image_bytes = base64.b64decode(image_base64)
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)


def preprocess_medical_image(image: np.ndarray) -> np.ndarray:
    """
    Apply medical-grade image preprocessing:
    - Resize large images to max 1024px on longest side
    - CLAHE (Contrast Limited Adaptive Histogram Equalization) on luminance channel
    - Slight Gaussian blur to reduce sensor noise
    """
    # Resize to manageable dimensions while maintaining aspect ratio
    h, w = image.shape[:2]
    max_dim = 1024
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        new_w, new_h = int(w * scale), int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # Convert to LAB for CLAHE on luminance
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)
    enhanced_lab = cv2.merge([l_enhanced, a, b])
    enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

    # Light denoising
    enhanced = cv2.GaussianBlur(enhanced, (3, 3), 0)
    return enhanced


def encode_to_base64(image: np.ndarray) -> str:
    """Encode an OpenCV image array back to base64 PNG."""
    _, buffer = cv2.imencode(".png", image)
    return base64.b64encode(buffer.tobytes()).decode("utf-8")


def parse_vision_response(raw_response: str) -> dict:
    """
    Parse the LLaVA response into structured fields.
    Attempts to extract: description, conditions, findings, confidence.
    """
    text = raw_response.strip()

    # Extract identified conditions (look for list-like patterns)
    conditions: List[str] = []
    findings: List[str] = []

    lines = text.split("\n")
    in_conditions = False
    in_findings = False
    description_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if "condition" in lower or "diagnos" in lower or "patholog" in lower:
            in_conditions = True
            in_findings = False
            continue
        if "finding" in lower or "observ" in lower or "feature" in lower:
            in_findings = True
            in_conditions = False
            continue
        if line.startswith(("-", "*", "•", "1", "2", "3", "4", "5")):
            cleaned = line.lstrip("-*•0123456789. ").strip()
            if in_conditions:
                conditions.append(cleaned)
            elif in_findings:
                findings.append(cleaned)
            else:
                description_lines.append(line)
        else:
            in_conditions = False
            in_findings = False
            description_lines.append(line)

    description = " ".join(description_lines) if description_lines else text
    if not conditions and not findings:
        description = text

    # Rough confidence based on response length and specificity
    confidence = min(0.9, 0.5 + len(text) / 2000)

    return {
        "description": description,
        "identified_conditions": conditions,
        "visual_findings": findings,
        "confidence": round(confidence, 2),
        "raw_response": text,
    }


MEDICAL_VISION_PROMPT = """You are a medical imaging AI assistant. Analyze this medical image carefully and provide:

1. A detailed description of what you observe
2. Any identified pathological conditions or abnormalities
3. Key visual findings (e.g., lesions, masses, fractures, opacities, discolorations)
4. Notable anatomical structures visible

Format your response with clear sections:
- Description: [overall image description]
- Identified Conditions: [list any suspected conditions]
- Visual Findings: [specific observations]

Be precise, clinical, and note any areas of uncertainty. This is for medical professional review."""

DESCRIBE_PROMPT = """Describe the contents of this image in detail. If it appears to be a medical image,
describe the anatomical structures, imaging modality (X-ray, MRI, CT, ultrasound, photo, etc.),
and any notable features. Be thorough and objective."""


async def analyze_image(image_base64: str, prompt: Optional[str] = None) -> dict:
    """Preprocess and analyze a medical image via llava through ollama_router_service."""
    # Preprocess
    try:
        image_array = decode_base64_image(image_base64)
        processed = preprocess_medical_image(image_array)
        processed_b64 = encode_to_base64(processed)
        preprocessing_applied = True
    except Exception:
        # If preprocessing fails, send original
        processed_b64 = image_base64
        preprocessing_applied = False

    analysis_prompt = prompt or MEDICAL_VISION_PROMPT

    payload = {
        "image_base64": processed_b64,
        "prompt": analysis_prompt,
    }

    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.post(
            f"{settings.ollama_router_url}/api/v1/model/vision",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    raw_response = data.get("response", "")
    parsed = parse_vision_response(raw_response)
    parsed["model"] = data.get("model", "llava:latest")
    parsed["preprocessing_applied"] = preprocessing_applied

    return parsed


async def describe_image(image_base64: str) -> dict:
    """Generate a plain-language description of the image contents."""
    return await analyze_image(image_base64, prompt=DESCRIBE_PROMPT)
