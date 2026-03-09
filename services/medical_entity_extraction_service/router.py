from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from service import extract_entities, ExtractedEntity, ENTITY_CONFIG

router = APIRouter(prefix="/api/v1/entities", tags=["entities"])


class ExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=10000, description="Medical text to extract entities from")
    entity_types: Optional[List[str]] = Field(
        default=None,
        description="Entity types to extract. If null, all types are extracted.",
        examples=[["symptom", "medication", "condition"]],
    )
    use_llm: bool = Field(default=True, description="Whether to use LLM augmentation")


class ExtractionResponse(BaseModel):
    entities: List[ExtractedEntity]
    total_found: int
    entity_types_searched: List[str]
    text_length: int


@router.post("/extract", response_model=ExtractionResponse)
async def extract_medical_entities(request: ExtractionRequest):
    """Extract medical entities (symptoms, medications, conditions, procedures, anatomy, measurements) from text."""
    valid_types = list(ENTITY_CONFIG.keys())
    if request.entity_types:
        invalid = [t for t in request.entity_types if t not in valid_types]
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid entity types: {invalid}. Valid types: {valid_types}",
            )

    entities = await extract_entities(
        text=request.text,
        entity_types=request.entity_types,
        use_llm=request.use_llm,
    )

    searched_types = request.entity_types if request.entity_types else valid_types

    return ExtractionResponse(
        entities=entities,
        total_found=len(entities),
        entity_types_searched=searched_types,
        text_length=len(request.text),
    )
