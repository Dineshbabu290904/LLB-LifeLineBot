import logging

from fastapi import APIRouter, HTTPException, Request, status

from service import ImageInput, MedicalQueryInput, SanitizeInput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/validate", tags=["validation"])


def _svc(request: Request):
    return request.app.state.validation_service


@router.post("/medical-query")
async def validate_medical_query(payload: MedicalQueryInput, request: Request):
    """
    Validate and sanitize a medical query.

    Checks: max length (2000), prompt injection, PII (email, phone, SSN).
    Returns sanitized text and a list of detected issues.
    """
    result = _svc(request).validate_medical_query(payload)
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"issues": result.issues, "result": result.model_dump()},
        )
    return result.model_dump()


@router.post("/image")
async def validate_image(payload: ImageInput, request: Request):
    """
    Validate a base64-encoded image.

    Checks: JPEG/PNG format (magic bytes), maximum size 5 MB.
    """
    result = _svc(request).validate_image(payload)
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"issues": result.issues, "result": result.model_dump()},
        )
    return result.model_dump()


@router.post("/sanitize")
async def sanitize_text(payload: SanitizeInput, request: Request):
    """
    Sanitize arbitrary text: remove PII and strip prompt-injection patterns.
    Always returns HTTP 200 with the cleaned text.
    """
    result = _svc(request).sanitize_text(payload)
    return result.model_dump()
