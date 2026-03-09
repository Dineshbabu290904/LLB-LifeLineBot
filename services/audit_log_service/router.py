from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from service import (
    record_audit_event,
    list_audit_events,
    count_audit_events,
    get_audit_event,
)

router = APIRouter()


class AuditEventRequest(BaseModel):
    session_id: str = Field(..., description="Session in which the action occurred")
    agent_name: str = Field(..., description="Name of the agent or service that performed the action")
    action: str = Field(..., description="Human-readable action label (e.g. 'triage_decision', 'llm_call')")
    input_data: Optional[str] = Field(
        None,
        description="Raw input text (will be stored only as SHA-256 hash for privacy)",
    )
    output_data: Optional[str] = Field(
        None,
        description="Raw output text (will be stored only as SHA-256 hash for privacy)",
    )
    user_id: Optional[str] = Field(None, description="Authenticated user ID if available")
    extra: Optional[dict] = Field(None, description="Supplementary structured metadata")


@router.post("/audit", status_code=201)
async def create_audit_event(req: AuditEventRequest):
    """
    Record an immutable audit event.
    Input/output are hashed (SHA-256) before storage — raw content is never persisted.
    """
    try:
        result = await record_audit_event(
            session_id=req.session_id,
            agent_name=req.agent_name,
            action=req.action,
            input_data=req.input_data,
            output_data=req.output_data,
            user_id=req.user_id,
            extra=req.extra,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to record audit event: {exc}")


@router.get("/audit")
async def list_events(
    session_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
):
    """List audit events with optional filters. Records are returned newest-first."""
    events = await list_audit_events(session_id, agent_name, action, from_date, to_date, limit, skip)
    total = await count_audit_events(session_id, agent_name, action, from_date, to_date)
    return {"total": total, "skip": skip, "limit": limit, "events": events}


@router.get("/audit/{audit_id}")
async def get_event(audit_id: str):
    """Retrieve a single audit event by its ID."""
    event = await get_audit_event(audit_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Audit event '{audit_id}' not found")
    return event
