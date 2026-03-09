"""
Request Validation & Sanitization Service

Responsibilities:
- Medical query validation (length, injection, PII)
- Base64 image validation (format, size)
- General text sanitization (PII redaction, prompt injection stripping)
"""

import base64
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)

MAX_QUERY_LENGTH = 2000
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_IMAGE_MAGIC: Dict[str, bytes] = {
    "jpeg": b"\xff\xd8\xff",
    "png": b"\x89PNG\r\n\x1a\n",
}

# ---------------------------------------------------------------------------
# PII patterns
# ---------------------------------------------------------------------------
_PII_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"),
        "[EMAIL]",
    ),
    (
        "phone_us",
        re.compile(
            r"(\+?1[\s\-.]?)?"
            r"\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}\b"
        ),
        "[PHONE]",
    ),
    (
        "ssn",
        re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b"),
        "[SSN]",
    ),
    (
        "credit_card",
        re.compile(r"\b(?:\d[ \-]?){13,16}\b"),
        "[CREDIT_CARD]",
    ),
    (
        "date_of_birth",
        re.compile(
            r"\b(0?[1-9]|1[0-2])[/\-\.](0?[1-9]|[12]\d|3[01])[/\-\.](\d{2}|\d{4})\b"
        ),
        "[DOB]",
    ),
]

# ---------------------------------------------------------------------------
# Prompt-injection patterns
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"forget\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an|the)\s+\w+", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:a|an|the)?\s*\w+", re.IGNORECASE),
    re.compile(r"(system|assistant|user)\s*:\s*", re.IGNORECASE),
    re.compile(r"<\|im_start\|>|<\|im_end\|>", re.IGNORECASE),
    re.compile(r"\[\s*INST\s*\]|\[/\s*INST\s*\]", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
    re.compile(r"execute\s+(this\s+)?code", re.IGNORECASE),
    re.compile(r"```[\s\S]*?```"),   # code blocks
]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MedicalQueryInput(BaseModel):
    query: str
    user_id: Optional[str] = None


class ImageInput(BaseModel):
    image_b64: str
    filename: Optional[str] = None


class SanitizeInput(BaseModel):
    text: str


class ValidationResult(BaseModel):
    valid: bool
    sanitized_text: Optional[str] = None
    issues: List[str] = []
    pii_found: List[str] = []
    injection_detected: bool = False
    image_format: Optional[str] = None
    image_size_bytes: Optional[int] = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class ValidationService:

    # ------------------------------------------------------------------
    # PII helpers
    # ------------------------------------------------------------------

    def _detect_and_redact_pii(self, text: str) -> Tuple[str, List[str]]:
        """Replace PII with placeholders and return the cleaned text + list of PII types found."""
        found: List[str] = []
        cleaned = text
        for pii_type, pattern, replacement in _PII_PATTERNS:
            new_text, n = pattern.subn(replacement, cleaned)
            if n > 0:
                found.append(pii_type)
                cleaned = new_text
        return cleaned, found

    # ------------------------------------------------------------------
    # Injection helpers
    # ------------------------------------------------------------------

    def _detect_injection(self, text: str) -> bool:
        return any(p.search(text) for p in _INJECTION_PATTERNS)

    def _strip_injection(self, text: str) -> str:
        """Remove matched injection patterns from text."""
        cleaned = text
        for pattern in _INJECTION_PATTERNS:
            cleaned = pattern.sub("", cleaned)
        return cleaned.strip()

    # ------------------------------------------------------------------
    # Public validators
    # ------------------------------------------------------------------

    def validate_medical_query(self, payload: MedicalQueryInput) -> ValidationResult:
        issues: List[str] = []
        query = payload.query

        # 1. Length check
        if len(query) > MAX_QUERY_LENGTH:
            issues.append(
                f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters "
                f"(got {len(query)})"
            )
            query = query[:MAX_QUERY_LENGTH]

        # 2. Injection check
        injection_detected = self._detect_injection(query)
        if injection_detected:
            issues.append("Potential prompt injection detected; patterns removed")
            query = self._strip_injection(query)

        # 3. PII detection & redaction
        sanitized, pii_found = self._detect_and_redact_pii(query)
        if pii_found:
            issues.append(f"PII detected and redacted: {', '.join(pii_found)}")

        valid = len([i for i in issues if "exceeds" in i]) == 0

        return ValidationResult(
            valid=valid,
            sanitized_text=sanitized,
            issues=issues,
            pii_found=pii_found,
            injection_detected=injection_detected,
        )

    def validate_image(self, payload: ImageInput) -> ValidationResult:
        issues: List[str] = []
        image_format: Optional[str] = None
        image_size: Optional[int] = None

        # 1. Decode base64
        try:
            # Strip data-URI prefix if present
            b64_data = payload.image_b64
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            raw = base64.b64decode(b64_data)
        except Exception as exc:
            return ValidationResult(
                valid=False,
                issues=[f"Invalid base64 encoding: {exc}"],
            )

        image_size = len(raw)

        # 2. Size check
        if image_size > MAX_IMAGE_BYTES:
            issues.append(
                f"Image size {image_size / (1024*1024):.2f} MB exceeds limit of 5 MB"
            )

        # 3. Magic-byte format check
        detected_format: Optional[str] = None
        for fmt, magic in ALLOWED_IMAGE_MAGIC.items():
            if raw[: len(magic)] == magic:
                detected_format = fmt
                break

        if detected_format is None:
            issues.append(
                "Unsupported image format. Only JPEG and PNG are allowed."
            )
        else:
            image_format = detected_format

        valid = len(issues) == 0

        return ValidationResult(
            valid=valid,
            issues=issues,
            image_format=image_format,
            image_size_bytes=image_size,
        )

    def sanitize_text(self, payload: SanitizeInput) -> ValidationResult:
        text = payload.text
        issues: List[str] = []

        injection_detected = self._detect_injection(text)
        if injection_detected:
            issues.append("Prompt injection patterns detected and removed")
            text = self._strip_injection(text)

        sanitized, pii_found = self._detect_and_redact_pii(text)
        if pii_found:
            issues.append(f"PII detected and redacted: {', '.join(pii_found)}")

        return ValidationResult(
            valid=True,
            sanitized_text=sanitized,
            issues=issues,
            pii_found=pii_found,
            injection_detected=injection_detected,
        )
