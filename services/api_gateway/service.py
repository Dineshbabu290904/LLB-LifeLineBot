"""
API Gateway Service

Handles:
- JWT verification (via auth_service)
- Rate limiting (via rate_limit_service)
- Request validation (via request_validation_service)
- Reverse-proxy forwarding to downstream microservices
"""

import logging
import os
from typing import Any, Dict, Optional

import httpx
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Downstream service URLs
    auth_service_url: str = os.getenv("AUTH_SERVICE_URL", "http://auth_service:8001")
    session_service_url: str = os.getenv("SESSION_SERVICE_URL", "http://session_service:8002")
    rate_limit_service_url: str = os.getenv(
        "RATE_LIMIT_SERVICE_URL", "http://rate_limit_service:8003"
    )
    validation_service_url: str = os.getenv(
        "VALIDATION_SERVICE_URL", "http://request_validation_service:8004"
    )
    langgraph_orchestrator_url: str = os.getenv(
        "LANGGRAPH_ORCHESTRATOR_URL", "http://langgraph_orchestrator:8010"
    )
    vision_agent_service_url: str = os.getenv(
        "VISION_AGENT_SERVICE_URL", "http://vision_agent_service:8023"
    )
    document_ingestion_service_url: str = os.getenv(
        "DOCUMENT_INGESTION_SERVICE_URL", "http://document_ingestion_service:8060"
    )
    dataset_storage_service_url: str = os.getenv(
        "DATASET_STORAGE_SERVICE_URL", "http://dataset_storage_service:8041"
    )
    evaluation_agent_url: str = os.getenv(
        "EVALUATION_AGENT_URL", "http://evaluation_agent:8029"
    )
    training_pipeline_service_url: str = os.getenv(
        "TRAINING_PIPELINE_SERVICE_URL", "http://training_pipeline_service:8111"
    )
    monitoring_service_url: str = os.getenv(
        "MONITORING_SERVICE_URL", "http://monitoring_service:8092"
    )

    http_timeout: float = 30.0

    class Config:
        env_file = ".env"


settings = Settings()

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class GatewayError(Exception):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


class AuthError(GatewayError):
    def __init__(self, message: str = "Unauthorised"):
        super().__init__(message, status_code=401)


class RateLimitError(GatewayError):
    def __init__(self, remaining: int = 0, reset_at: Optional[str] = None):
        msg = f"Rate limit exceeded. Remaining: {remaining}. Reset at: {reset_at}"
        super().__init__(msg, status_code=429)
        self.remaining = remaining
        self.reset_at = reset_at


class ValidationError(GatewayError):
    def __init__(self, issues: list):
        super().__init__(f"Request validation failed: {issues}", status_code=422)
        self.issues = issues


# ---------------------------------------------------------------------------
# Gateway service
# ---------------------------------------------------------------------------


class GatewayService:
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self):
        self._client = httpx.AsyncClient(timeout=settings.http_timeout)
        logger.info("Gateway HTTP client initialised.")

    async def stop(self):
        if self._client:
            await self._client.aclose()
        logger.info("Gateway HTTP client closed.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("HTTP client not initialised")
        return self._client

    async def _post_json(self, url: str, payload: dict) -> dict:
        try:
            resp = await self.client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise GatewayError(
                f"Upstream {url} returned {exc.response.status_code}: {exc.response.text}",
                status_code=502,
            )
        except httpx.RequestError as exc:
            raise GatewayError(f"Could not reach {url}: {exc}", status_code=503)

    async def _proxy(
        self,
        method: str,
        target_url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Any] = None,
        content: Optional[bytes] = None,
        params: Optional[dict] = None,
    ) -> httpx.Response:
        """Low-level proxy: forward a request to a downstream service and return the raw response."""
        try:
            resp = await self.client.request(
                method,
                target_url,
                headers=headers or {},
                json=json_body,
                content=content,
                params=params,
            )
            return resp
        except httpx.RequestError as exc:
            raise GatewayError(f"Could not reach {target_url}: {exc}", status_code=503)

    # ------------------------------------------------------------------
    # Cross-cutting concerns
    # ------------------------------------------------------------------

    async def verify_token(self, token: str) -> dict:
        """Call auth_service to validate a Bearer token. Returns the token claims."""
        result = await self._post_json(
            f"{settings.auth_service_url}/api/v1/auth/verify",
            {"token": token},
        )
        if not result.get("valid"):
            raise AuthError("Token is not valid")
        return result

    async def check_rate_limit(self, client_id: str) -> None:
        """Call rate_limit_service. Raises RateLimitError if the client is over quota."""
        result = await self._post_json(
            f"{settings.rate_limit_service_url}/api/v1/rate-limit/check",
            {"client_id": client_id},
        )
        if not result.get("allowed", True):
            raise RateLimitError(
                remaining=result.get("remaining", 0),
                reset_at=result.get("reset_at"),
            )

    async def validate_query(self, query: str, user_id: Optional[str] = None) -> str:
        """
        Validate and sanitize a medical query.
        Returns the sanitized version.
        Raises ValidationError on hard failures.
        """
        result = await self._post_json(
            f"{settings.validation_service_url}/api/v1/validate/medical-query",
            {"query": query, "user_id": user_id},
        )
        if not result.get("valid", True):
            raise ValidationError(issues=result.get("issues", []))
        return result.get("sanitized_text", query)

    # ------------------------------------------------------------------
    # Convenience: full pre-flight check
    # ------------------------------------------------------------------

    async def preflight(
        self,
        authorization: Optional[str],
        client_id: str,
        query: Optional[str] = None,
    ) -> dict:
        """
        Run auth → rate-limit → (optional) query validation in sequence.
        Returns the auth claims dict.
        """
        # 1. Auth
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthError("Missing or malformed Authorization header")
        token = authorization.split(" ", 1)[1]
        claims = await self.verify_token(token)

        # 2. Rate limit (use user_id as the stable client identifier)
        effective_client = claims.get("user_id", client_id)
        await self.check_rate_limit(effective_client)

        # 3. Query validation (optional)
        sanitized_query: Optional[str] = None
        if query is not None:
            sanitized_query = await self.validate_query(query, user_id=effective_client)

        return {
            "claims": claims,
            "client_id": effective_client,
            "sanitized_query": sanitized_query,
        }

    # ------------------------------------------------------------------
    # Proxy helpers for each downstream
    # ------------------------------------------------------------------

    async def forward(
        self,
        method: str,
        target_url: str,
        *,
        json_body: Optional[Any] = None,
        content: Optional[bytes] = None,
        extra_headers: Optional[Dict[str, str]] = None,
        params: Optional[dict] = None,
    ) -> httpx.Response:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        return await self._proxy(
            method,
            target_url,
            headers=headers,
            json_body=json_body,
            content=content,
            params=params,
        )
