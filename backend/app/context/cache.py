from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from app.core.redis import get_redis_client


logger = logging.getLogger(__name__)
CONTEXT_CACHE_TTL_SECONDS = 300


async def cache_get(key: str) -> Any | None:
    client = get_redis_client()
    if client is None:
        return None
    try:
        value = await client.get(key)
        return json.loads(value) if value else None
    except Exception:
        logger.warning("Context cache read failed", exc_info=True)
        return None


async def cache_set(key: str, value: Any) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(value, default=str), ex=CONTEXT_CACHE_TTL_SECONDS)
    except Exception:
        logger.warning("Context cache write failed", exc_info=True)


async def invalidate_company(tenant_id: UUID) -> None:
    await _delete(f"context:company:{tenant_id}")


async def invalidate_user(tenant_id: UUID, user_id: UUID) -> None:
    await _delete(
        f"context:lens:{tenant_id}:{user_id}",
        f"context:focus:{tenant_id}:{user_id}",
    )


async def _delete(*keys: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        await client.delete(*keys)
        await client.publish("context:invalidated", json.dumps({"keys": keys}))
    except Exception:
        logger.warning("Context cache invalidation failed", exc_info=True)
