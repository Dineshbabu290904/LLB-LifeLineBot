from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from service import LogEntry, store_log, query_logs, count_logs

router = APIRouter()


class LogResponse(BaseModel):
    id: str
    status: str


class LogsListResponse(BaseModel):
    total: int
    skip: int
    limit: int
    logs: list


@router.post("/logs", response_model=LogResponse, status_code=201)
async def create_log(entry: LogEntry):
    """Ingest a single log entry from any MEDBOT service."""
    try:
        result = await store_log(entry)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to store log: {exc}")


@router.get("/logs", response_model=LogsListResponse)
async def list_logs(
    service: Optional[str] = Query(None, description="Filter by service name"),
    level: Optional[str] = Query(None, description="Filter by log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)"),
    from_date: Optional[datetime] = Query(None, description="Include logs at or after this timestamp (ISO 8601)"),
    to_date: Optional[datetime] = Query(None, description="Include logs at or before this timestamp (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
):
    """Query stored log entries with optional filters."""
    try:
        logs = await query_logs(service, level, from_date, to_date, limit, skip)
        total = await count_logs(service, level, from_date, to_date)
        return {"total": total, "skip": skip, "limit": limit, "logs": logs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query logs: {exc}")


@router.delete("/logs", status_code=204)
async def clear_logs(
    service: Optional[str] = Query(None, description="Delete only logs from this service"),
    level: Optional[str] = Query(None, description="Delete only logs with this level"),
):
    """Delete log entries (admin operation). Requires at least one filter to prevent accidental wipe."""
    from service import get_db
    if not service and not level:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one filter (service or level) to avoid clearing the entire collection.",
        )
    db = await get_db()
    query: dict = {}
    if service:
        query["service"] = service
    if level:
        query["level"] = level.upper()
    await db["logs"].delete_many(query)
