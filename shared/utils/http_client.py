import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 3


async def get_http_client(timeout: float = DEFAULT_TIMEOUT) -> httpx.AsyncClient:
    """Create a reusable async HTTP client."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout),
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )


class ServiceClient:
    """HTTP client for calling internal microservices."""

    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                headers={"Content-Type": "application/json"},
                follow_redirects=True,
            )
        return self._client

    async def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        client = await self._get_client()
        response = await client.post(path, json=data)
        response.raise_for_status()
        return response.json()

    async def health_check(self) -> bool:
        try:
            result = await self.get("/health")
            return result.get("status") == "ok"
        except Exception as e:
            logger.warning(f"Health check failed for {self.base_url}: {e}")
            return False

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
