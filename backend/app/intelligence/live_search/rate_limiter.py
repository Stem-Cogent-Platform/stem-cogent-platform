from __future__ import annotations

import logging
import time
from collections import defaultdict
from uuid import UUID

from app.core.config import get_settings
from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

# Fallback in-memory rate tracker: tenant_id -> list of unix timestamps
_IN_MEMORY_RATES: dict[str, list[float]] = defaultdict(list)


class LiveSearchRateLimiter:
    """Per-tenant live search rate limiter supporting Redis and resilient in-memory fallback."""

    def __init__(self, limit_per_minute: int | None = None) -> None:
        self._limit = (
            limit_per_minute
            if limit_per_minute is not None
            else get_settings().LIVE_SEARCH_RATE_LIMIT_PER_MINUTE
        )

    async def check_and_increment(
        self, tenant_id: str | UUID
    ) -> tuple[bool, int, int]:
        """Check if tenant is within quota and record usage.

        Returns:
            (allowed: bool, current_count: int, retry_after_seconds: int)
        """
        tid = str(tenant_id)
        redis_client = get_redis_client()

        if redis_client is not None:
            try:
                key = f"live_search:rate:{tid}"
                count = await redis_client.incr(key)
                if count == 1:
                    await redis_client.expire(key, 60)
                ttl = await redis_client.ttl(key)
                retry_after = max(1, ttl) if ttl > 0 else 60
                allowed = count <= self._limit
                return allowed, count, retry_after
            except Exception as exc:
                logger.warning(
                    "Redis rate limiting failed for live search; falling back to in-memory window",
                    extra={"error": str(exc)},
                )

        # In-memory fallback
        now = time.time()
        window_start = now - 60.0
        # Evict timestamps older than 60s
        timestamps = [ts for ts in _IN_MEMORY_RATES[tid] if ts > window_start]
        timestamps.append(now)
        _IN_MEMORY_RATES[tid] = timestamps

        count = len(timestamps)
        allowed = count <= self._limit
        oldest = timestamps[0] if timestamps else now
        retry_after = max(1, int(60.0 - (now - oldest)))
        return allowed, count, retry_after

    def reset_in_memory(self) -> None:
        """Reset in-memory storage (useful for unit testing)."""
        _IN_MEMORY_RATES.clear()
