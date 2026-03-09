import logging

from fastapi import APIRouter, HTTPException, Request, status

from service import RateLimitCheck

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rate-limit", tags=["rate-limit"])


def _svc(request: Request):
    return request.app.state.rate_limit_service


@router.post("/check")
async def check_rate_limit(payload: RateLimitCheck, request: Request):
    """
    Check whether a client is within the allowed rate limit.
    Records the request if allowed.
    """
    try:
        result = await _svc(request).check(payload.client_id)
        return result.model_dump()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.get("/status/{client_id}")
async def get_status(client_id: str, request: Request):
    """Return current rate limit usage for a client without recording a request."""
    try:
        result = await _svc(request).status(client_id)
        return result.model_dump()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/reset/{client_id}", status_code=status.HTTP_200_OK)
async def reset_limit(client_id: str, request: Request):
    """Reset (clear) the rate limit counter for a given client."""
    try:
        result = await _svc(request).reset(client_id)
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
