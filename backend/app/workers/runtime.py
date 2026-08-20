from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.database import close_database_connection
from app.core.redis import close_redis_connection


T = TypeVar("T")


def run_async_worker(operation: Callable[[], Awaitable[T]]) -> T:
    """Run one sync Celery task without leaking clients across event loops."""

    async def runner() -> T:
        try:
            return await operation()
        finally:
            try:
                await close_database_connection()
            finally:
                await close_redis_connection()

    return asyncio.run(runner())
