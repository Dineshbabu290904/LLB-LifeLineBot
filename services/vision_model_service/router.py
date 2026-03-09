"""
Vision Model Service - API route definitions.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from service import analyze_image, describe_image

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])


class AnalyzeRequest(BaseModel):
    image_base64: str = Field(
        ..., description="Base64-encoded medical image (JPEG, PNG, DICOM-exported PNG)"
    )
    prompt: Optional[str] = Field(
        None, description="Custom analysis prompt; defaults to structured medical analysis"
    )


class AnalyzeResponse(BaseModel):
    description: str
    identified_conditions: list
    visual_findings: list
    confidence: float
    model: str
    preprocessing_applied: bool
    raw_response: str


class DescribeRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded image to describe")


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_medical_image(request: AnalyzeRequest):
    """
    Analyze a medical image using LLaVA vision model.
    Applies CLAHE contrast enhancement and noise reduction before inference.
    Returns structured findings: description, conditions, visual findings, confidence.
    """
    try:
        result = await analyze_image(
            image_base64=request.image_base64,
            prompt=request.prompt,
        )
        return AnalyzeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Vision analysis failed: {str(e)}")


@router.post("/describe")
async def describe_image_contents(request: DescribeRequest):
    """
    Generate a plain-language description of the image contents.
    Identifies imaging modality and notable anatomical or pathological features.
    """
    try:
        result = await describe_image(image_base64=request.image_base64)
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Image description failed: {str(e)}")
