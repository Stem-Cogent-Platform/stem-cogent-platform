from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.core.config import get_settings
from app.intelligence.live_search.client import (
    LiveSearchClient,
    LiveSearchError,
    LiveSearchRateLimitError,
    LiveSearchTimeoutError,
    SerpApiClient,
)
from app.intelligence.live_search.models import (
    LiveSearchExecutionResult,
    LiveSearchLifecycle,
)
from app.intelligence.live_search.normalizer import normalize_and_dedup_search_results
from app.intelligence.live_search.privacy import sanitize_live_search_query
from app.intelligence.live_search.rate_limiter import LiveSearchRateLimiter

logger = logging.getLogger(__name__)


class LiveSearchService:
    """Production service coordinating live search privacy, limits, retrieval, and normalization."""

    def __init__(
        self,
        *,
        client: LiveSearchClient | None = None,
        rate_limiter: LiveSearchRateLimiter | None = None,
    ) -> None:
        self._client = client or SerpApiClient()
        self._rate_limiter = rate_limiter or LiveSearchRateLimiter()

    async def execute_live_search(
        self,
        query: str,
        *,
        tenant_id: str | UUID,
        public_entities: list[str] | None = None,
        company_context: dict[str, Any] | None = None,
        exclude_urls: set[str] | None = None,
        num_results: int = 5,
        lifecycle: LiveSearchLifecycle = LiveSearchLifecycle.INVESTIGATION_EVIDENCE,
    ) -> LiveSearchExecutionResult:
        settings = get_settings()

        # 1. Feature flag check
        if not settings.LIVE_SEARCH_ENABLED:
            return LiveSearchExecutionResult(
                status="SKIPPED_DISABLED",
                query=query,
                sanitized_query="",
                results=[],
                error_message="Live search capability is currently disabled by configuration.",
            )

        # 2. Sanitize query via strict privacy boundary
        sanitized = sanitize_live_search_query(
            query,
            public_entities=public_entities,
            company_context=company_context,
        )

        # 3. Check client configuration
        if hasattr(self._client, "is_configured") and not self._client.is_configured:
            return LiveSearchExecutionResult(
                status="SKIPPED_UNCONFIGURED",
                query=query,
                sanitized_query=sanitized,
                results=[],
                error_message="Live search provider credentials are not configured.",
            )

        # 4. Check tenant rate limit
        allowed, count, retry_after = await self._rate_limiter.check_and_increment(tenant_id)
        if not allowed:
            logger.warning(
                "Tenant live search rate limit exceeded",
                extra={"tenant_id": str(tenant_id), "count": count, "retry_after": retry_after},
            )
            return LiveSearchExecutionResult(
                status="RATE_LIMITED",
                query=query,
                sanitized_query=sanitized,
                results=[],
                error_message=f"Live search rate limit exceeded. Retry after {retry_after} seconds.",
            )

        # 5. Execute external search with graceful degradation
        try:
            raw_results = await self._client.search(sanitized, num_results=num_results)
        except LiveSearchTimeoutError:
            return LiveSearchExecutionResult(
                status="TIMEOUT",
                query=query,
                sanitized_query=sanitized,
                results=[],
                error_message="External search provider request timed out. Retrying or internal fallback advised.",
            )
        except LiveSearchRateLimitError:
            return LiveSearchExecutionResult(
                status="PROVIDER_RATE_LIMITED",
                query=query,
                sanitized_query=sanitized,
                results=[],
                error_message="External search provider rate limit exhausted.",
            )
        except LiveSearchError as exc:
            return LiveSearchExecutionResult(
                status="PROVIDER_ERROR",
                query=query,
                sanitized_query=sanitized,
                results=[],
                error_message=str(exc),
            )
        except Exception as exc:
            logger.exception("Unexpected error in live search client execution")
            return LiveSearchExecutionResult(
                status="PROVIDER_ERROR",
                query=query,
                sanitized_query=sanitized,
                results=[],
                error_message=f"Live search service error: {type(exc).__name__}",
            )

        # 6. Normalize and deduplicate results
        normalized = normalize_and_dedup_search_results(
            raw_results,
            query_used=sanitized,
            exclude_urls=exclude_urls,
            lifecycle=lifecycle,
        )

        status = "SUCCESS" if normalized else "NO_RESULTS"
        return LiveSearchExecutionResult(
            status=status,
            query=query,
            sanitized_query=sanitized,
            results=normalized,
        )

    async def aclose(self) -> None:
        if hasattr(self._client, "aclose"):
            await self._client.aclose()
