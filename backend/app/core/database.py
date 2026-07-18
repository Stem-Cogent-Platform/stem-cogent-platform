import asyncio
from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _database_url() -> str | None:
    database_url = get_settings().DATABASE_URL
    if database_url is None:
        return None
    return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


def get_engine() -> AsyncEngine | None:
    global _engine, _session_factory

    if _engine is None:
        database_url = _database_url()
        if database_url is None:
            return None
        _engine = create_async_engine(database_url, pool_pre_ping=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)

    return _engine


async def get_session() -> AsyncIterator[AsyncSession]:
    get_engine()
    if _session_factory is None:
        raise RuntimeError("Database is not configured")
    async with _session_factory() as session:
        yield session


async def check_database_connection() -> str:
    engine = get_engine()
    if engine is None:
        return "not_configured"

    try:
        async with asyncio.timeout(2):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception:
        return "unavailable"

    return "ok"


async def close_database_connection() -> None:
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
