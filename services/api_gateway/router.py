"""
API Gateway Router

Each endpoint runs the pre-flight check (auth + rate-limit + validation where
applicable) and then proxies the request body to the appropriate downstream
service, streaming the response back to the caller.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel

from service import AuthError, GatewayError, GatewayService, RateLimitError, ValidationError, settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["gateway"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _svc(request: Request) -> GatewayService:
    return request.app.state.gateway_service


def _client_ip(request: Request) -> str:
    """Best-effort client identifier (IP address or forwarded header)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _raise_gateway_error(exc: GatewayError):
    detail: Any = str(exc)
    if isinstance(exc, RateLimitError):
        detail = {
            "error": str(exc),
            "remaining": exc.remaining,
            "reset_at": exc.reset_at,
        }
    elif isinstance(exc, ValidationError):
        detail = {"error": str(exc), "issues": exc.issues}
    raise HTTPException(status_code=exc.status_code, detail=detail)


async def _preflight(
    request: Request,
    authorization: Optional[str],
    query: Optional[str] = None,
) -> dict:
    svc = _svc(request)
    client_id = _client_ip(request)
    try:
        return await svc.preflight(authorization, client_id, query=query)
    except GatewayError as exc:
        _raise_gateway_error(exc)


def _proxy_response(upstream: Any) -> Response:
    """Convert an httpx.Response into a FastAPI Response."""
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


# ---------------------------------------------------------------------------
# Schemas for gateway-level request bodies
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ImageAnalysisRequest(BaseModel):
    image_b64: str
    session_id: Optional[str] = None
    prompt: Optional[str] = None


class IngestRequest(BaseModel):
    document_url: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TrainTriggerRequest(BaseModel):
    model_name: str
    dataset_id: str
    hyperparams: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/api/v1/chat")
async def chat(
    payload: ChatRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    """
    Forward a medical chat query to the LangGraph orchestrator.
    Runs auth → rate-limit → query validation before forwarding.
    """
    ctx = await _preflight(request, authorization, query=payload.query)
    sanitized_query = ctx["sanitized_query"] or payload.query

    body = payload.model_dump()
    body["query"] = sanitized_query
    body["user_id"] = ctx["claims"].get("user_id")

    svc = _svc(request)
    try:
        upstream = await svc.forward(
            "POST",
            f"{settings.langgraph_orchestrator_url}/api/v1/chat",
            json_body=body,
        )
    except GatewayError as exc:
        _raise_gateway_error(exc)

    return _proxy_response(upstream)


@router.post("/api/v1/analyze/image")
async def analyze_image(
    payload: ImageAnalysisRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    """
    Forward an image analysis request to the vision agent service.
    Validates the image via request_validation_service first.
    """
    ctx = await _preflight(request, authorization)
    svc = _svc(request)

    # Image-specific validation
    try:
        await svc._post_json(
            f"{settings.validation_service_url}/api/v1/validate/image",
            {"image_b64": payload.image_b64, "filename": None},
        )
    except GatewayError as exc:
        _raise_gateway_error(exc)

    body = payload.model_dump()
    body["user_id"] = ctx["claims"].get("user_id")

    try:
        upstream = await svc.forward(
            "POST",
            f"{settings.vision_agent_service_url}/api/v1/analyze/image",
            json_body=body,
        )
    except GatewayError as exc:
        _raise_gateway_error(exc)

    return _proxy_response(upstream)


@router.get("/api/v1/session/{session_id}")
async def get_session(
    session_id: str,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    """Proxy session retrieval to the session service."""
    await _preflight(request, authorization)
    svc = _svc(request)
    try:
        upstream = await svc.forward(
            "GET",
            f"{settings.session_service_url}/api/v1/sessions/{session_id}",
        )
    except GatewayError as exc:
        _raise_gateway_error(exc)
    return _proxy_response(upstream)


@router.post("/api/v1/documents/ingest")
async def ingest_document(
    payload: IngestRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    """Forward a document ingestion request to the document ingestion service."""
    ctx = await _preflight(request, authorization)
    svc = _svc(request)

    body = payload.model_dump()
    body["user_id"] = ctx["claims"].get("user_id")

    try:
        upstream = await svc.forward(
            "POST",
            f"{settings.document_ingestion_service_url}/api/v1/documents/ingest",
            json_body=body,
        )
    except GatewayError as exc:
        _raise_gateway_error(exc)

    return _proxy_response(upstream)


@router.get("/api/v1/datasets")
async def list_datasets(
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    """Proxy dataset listing to the dataset storage service."""
    ctx = await _preflight(request, authorization)
    svc = _svc(request)
    try:
        upstream = await svc.forward(
            "GET",
            f"{settings.dataset_storage_service_url}/api/v1/datasets",
            params=dict(request.query_params),
        )
    except GatewayError as exc:
        _raise_gateway_error(exc)
    return _proxy_response(upstream)


@router.get("/api/v1/evaluation/{evaluation_id}")
async def get_evaluation(
    evaluation_id: str,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    """Proxy evaluation result retrieval to the evaluation agent."""
    await _preflight(request, authorization)
    svc = _svc(request)
    try:
        upstream = await svc.forward(
            "GET",
            f"{settings.evaluation_agent_url}/api/v1/evaluation/{evaluation_id}",
        )
    except GatewayError as exc:
        _raise_gateway_error(exc)
    return _proxy_response(upstream)


@router.post("/api/v1/train/trigger")
async def trigger_training(
    payload: TrainTriggerRequest,
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    """Proxy training pipeline trigger to the training pipeline service."""
    ctx = await _preflight(request, authorization)
    svc = _svc(request)

    body = payload.model_dump()
    body["triggered_by"] = ctx["claims"].get("user_id")

    try:
        upstream = await svc.forward(
            "POST",
            f"{settings.training_pipeline_service_url}/api/v1/train/trigger",
            json_body=body,
        )
    except GatewayError as exc:
        _raise_gateway_error(exc)

    return _proxy_response(upstream)


@router.get("/api/v1/health/all")
async def health_all(
    request: Request,
    authorization: Optional[str] = Header(default=None),
):
    """
    Aggregate health check.
    Auth is still required; forwards to the monitoring service which fans out
    to all other services.
    """
    await _preflight(request, authorization)
    svc = _svc(request)
    try:
        upstream = await svc.forward(
            "GET",
            f"{settings.monitoring_service_url}/api/v1/health/all",
        )
    except GatewayError as exc:
        _raise_gateway_error(exc)
    return _proxy_response(upstream)
