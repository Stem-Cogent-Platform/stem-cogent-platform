import asyncio
import logging

from redis.asyncio import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Redis | None = None


def _redis_url() -> str | None:
    settings = get_settings()
    if settings.REDIS_URL is not None:
        return settings.REDIS_URL
    if settings.REDIS_HOST is None:
        return None
    return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"


def get_redis_client() -> Redis | None:
    global _client

    if _client is None:
        redis_url = _redis_url()
        if redis_url is None:
            return None
        _client = Redis.from_url(redis_url, decode_responses=True)

    return _client


async def check_redis_connection() -> str:
    client = get_redis_client()
    if client is None:
        return "not_configured"

    try:
        async with asyncio.timeout(1):
            await client.ping()
    except Exception:
        logger.exception("Redis readiness check failed")
        return "unavailable"

    return "ok"


async def close_redis_connection() -> None:
    global _client

    if _client is not None:
        await _client.aclose()
    _client = None
