import logging

from fastapi import APIRouter, HTTPException, Request, status

from service import SessionCreate, SessionUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def _svc(request: Request):
    return request.app.state.session_service


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_session(payload: SessionCreate, request: Request):
    """Create a new session for a user."""
    try:
        session = await _svc(request).create_session(payload)
        return {"success": True, "session": session.model_dump()}
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/{session_id}")
async def get_session(session_id: str, request: Request):
    """Retrieve an existing session by ID."""
    try:
        session = await _svc(request).get_session(session_id)
        return {"success": True, "session": session.model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.put("/{session_id}")
async def update_session(session_id: str, payload: SessionUpdate, request: Request):
    """Update session context, preferences, or metadata."""
    try:
        session = await _svc(request).update_session(session_id, payload)
        return {"success": True, "session": session.model_dump()}
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.delete("/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Terminate (delete) a session."""
    try:
        deleted = await _svc(request).delete_session(session_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session '{session_id}' not found",
            )
        return {"success": True, "message": f"Session '{session_id}' terminated"}
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
