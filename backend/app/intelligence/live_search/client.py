from __future__ import annotations

import logging
from typing import Any, Protocol

import httpx

from app.core.config import get_settings
from app.core.secrets import get_scalar_secret

logger = logging.getLogger(__name__)


class LiveSearchError(RuntimeError):
    """Base exception for live search failures."""


class LiveSearchTimeoutError(LiveSearchError):
    """Raised when external search provider times out."""


class LiveSearchRateLimitError(LiveSearchError):
    """Raised when external search provider reports rate limit / quota exhaustion."""


class LiveSearchProviderError(LiveSearchError):
    """Raised when external search provider returns an error response."""


class LiveSearchClient(Protocol):
    """Protocol for external live search providers."""

    async def search(self, query: str, *, num_results: int = 5) -> list[dict[str, Any]]: ...

    async def aclose(self) -> None: ...


class SerpApiClient:
    """Async server-side client for SerpApi discovery."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        engine: str | None = None,
        timeout_seconds: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self._key = api_key or self._resolve_api_key()
        self._base_url = base_url or settings.SERPAPI_BASE_URL
        self._engine = engine or settings.SERPAPI_ENGINE
        self._timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.LIVE_SEARCH_TIMEOUT_SECONDS
        )
        self._client = http_client or httpx.AsyncClient(timeout=self._timeout)
        self._owns_client = http_client is None

    @staticmethod
    def _resolve_api_key() -> str | None:
        settings = get_settings()
        if settings.SERPAPI_API_KEY_ARN:
            try:
                return get_scalar_secret(settings.SERPAPI_API_KEY_ARN)
            except Exception as exc:
                logger.warning(
                    "Failed to resolve SerpApi secret from Secrets Manager",
                    extra={"error": type(exc).__name__},
                )
        return settings.SERPAPI_API_KEY

    @property
    def is_configured(self) -> bool:
        return bool(self._key)

    async def search(self, query: str, *, num_results: int = 5) -> list[dict[str, Any]]:
        if not self._key:
            raise LiveSearchProviderError(
                "Live search provider secret is not configured in this environment"
            )

        params: dict[str, Any] = {
            "engine": self._engine,
            "q": query,
            "gl": "ng",
            "hl": "en",
            "num": min(max(num_results, 1), 10),
            "api_key": self._key,
        }

        try:
            response = await self._client.get(self._base_url, params=params)
        except httpx.TimeoutException as exc:
            logger.warning(
                "Live search provider timed out",
                extra={"timeout_seconds": self._timeout, "engine": self._engine},
            )
            raise LiveSearchTimeoutError("Live search timed out") from exc
        except httpx.RequestError as exc:
            logger.warning(
                "Live search network request error",
                extra={"error_type": type(exc).__name__},
            )
            raise LiveSearchProviderError("Live search network connection failed") from exc

        if response.status_code == 429:
            logger.warning("Live search provider rate limit exceeded (429)")
            raise LiveSearchRateLimitError("Live search provider rate limit exceeded")

        if response.status_code != 200:
            logger.warning(
                "Live search provider error",
                extra={"status_code": response.status_code},
            )
            raise LiveSearchProviderError(
                f"Live search provider returned HTTP {response.status_code}"
            )

        try:
            data = response.json()
        except Exception as exc:
            raise LiveSearchProviderError("Live search response was not valid JSON") from exc

        # Organic results from Google SerpApi
        organic = data.get("organic_results")
        if isinstance(organic, list):
            return organic

        # News results if present
        news = data.get("news_results")
        if isinstance(news, list):
            return news

        return []

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()
