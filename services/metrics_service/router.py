from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from service import record_metric, get_summary, reset_metrics

router = APIRouter()


class MetricEvent(BaseModel):
    service: str = Field(..., description="Name of the originating service")
    event_type: str = Field("request", description="Event category: request | error | triage")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    triage_level: Optional[str] = Field(None, description="Triage severity (e.g. low/medium/high/critical)")
    is_error: bool = Field(False, description="Whether this event represents an error")
    extra: Optional[dict] = Field(None, description="Arbitrary additional metadata")


class MetricResponse(BaseModel):
    status: str
    event_type: str
    service: str
    timestamp: str


@router.post("/metrics/record", response_model=MetricResponse, status_code=201)
async def record(event: MetricEvent):
    """Record a single metric event from any MEDBOT service."""
    try:
        result = await record_metric(
            service=event.service,
            event_type=event.event_type,
            response_time_ms=event.response_time_ms,
            triage_level=event.triage_level,
            is_error=event.is_error,
            extra=event.extra,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to record metric: {exc}")


@router.get("/metrics/summary")
async def summary():
    """Return an aggregated metrics summary across all services."""
    try:
        return await get_summary()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve summary: {exc}")


@router.post("/metrics/reset", status_code=200)
async def reset():
    """Reset all metrics counters to zero (admin operation)."""
    try:
        return await reset_metrics()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to reset metrics: {exc}")
