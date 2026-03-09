from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from typing import Optional
from service import (
    store_dataset,
    list_datasets,
    get_dataset,
    export_as_jsonl,
    count_datasets,
)

router = APIRouter()


class DatasetRecord(BaseModel):
    source: str = Field(..., description="Origin of this record (e.g. 'conversation', 'pubmed', 'manual')")
    prompt: str = Field(..., description="Input prompt / user query")
    response: str = Field(..., description="Expected model response")
    quality_score: float = Field(
        ..., ge=0.0, le=1.0, description="Quality score between 0.0 (poor) and 1.0 (excellent)"
    )
    triage_label: Optional[str] = Field(None, description="Triage severity label if applicable")
    metadata: Optional[dict] = Field(None, description="Arbitrary extra metadata")


@router.post("/datasets", status_code=201)
async def create_dataset(record: DatasetRecord):
    """Store a new training dataset record."""
    result = await store_dataset(
        source=record.source,
        prompt=record.prompt,
        response=record.response,
        quality_score=record.quality_score,
        triage_label=record.triage_label,
        metadata=record.metadata,
    )
    return result


@router.get("/datasets")
async def list_all(
    min_quality: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum quality score filter"),
    source: Optional[str] = Query(None, description="Filter by data source"),
    triage_label: Optional[str] = Query(None, description="Filter by triage label"),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
):
    """List dataset records with optional quality and source filters."""
    records = await list_datasets(min_quality, source, triage_label, limit, skip)
    total = await count_datasets(min_quality, source, triage_label)
    return {"total": total, "skip": skip, "limit": limit, "records": records}


@router.get("/datasets/export", response_class=PlainTextResponse)
async def export(
    min_quality: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum quality score"),
    source: Optional[str] = Query(None),
    triage_label: Optional[str] = Query(None),
    limit: int = Query(10000, ge=1, le=100000, description="Maximum number of rows to export"),
):
    """
    Export dataset records as JSONL (one JSON object per line).
    Suitable for direct ingestion into fine-tuning pipelines.
    """
    jsonl = await export_as_jsonl(min_quality, source, triage_label, limit)
    return PlainTextResponse(content=jsonl, media_type="application/x-ndjson")


@router.get("/datasets/{dataset_id}")
async def get(dataset_id: str):
    """Retrieve a single dataset record by ID."""
    record = await get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Dataset record '{dataset_id}' not found")
    return record
