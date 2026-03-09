import logging

from fastapi import APIRouter, HTTPException, Request, status

from service import (
    TokenRefresh,
    TokenVerify,
    UserCreate,
    UserLogin,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _svc(request: Request):
    return request.app.state.auth_service


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, request: Request):
    """Register a new user account."""
    try:
        user = await _svc(request).register(payload)
        return {"success": True, "user": user.model_dump()}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/login")
async def login(payload: UserLogin, request: Request):
    """Authenticate user and return JWT tokens."""
    try:
        tokens = await _svc(request).login(payload)
        return tokens.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))


@router.post("/verify")
async def verify(payload: TokenVerify, request: Request):
    """Verify a JWT access token and return its claims."""
    try:
        result = await _svc(request).verify(payload)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post("/refresh")
async def refresh(payload: TokenRefresh, request: Request):
    """Use a refresh token to issue a new access/refresh token pair."""
    try:
        tokens = await _svc(request).refresh(payload)
        return tokens.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
