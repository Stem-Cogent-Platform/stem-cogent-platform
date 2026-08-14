import asyncio
import logging
from collections.abc import AsyncIterator

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.secrets import SecretConfigurationError, get_json_secret

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str | None:
    settings = get_settings()
    if settings.DATABASE_URL is not None:
        return settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

    credentials_arn = getattr(settings, "DATABASE_CREDENTIALS_ARN", None)
    database_host = getattr(settings, "DATABASE_HOST", None)
    if not credentials_arn or not database_host:
        return None

    credentials = get_json_secret(credentials_arn)
    username = credentials.get("username")
    password = credentials.get("password")
    if not isinstance(username, str) or not username or not isinstance(password, str) or not password:
        raise SecretConfigurationError("Database credentials secret requires non-empty username and password fields")

    return URL.create(
        drivername="postgresql+asyncpg",
        username=username,
        password=password,
        host=database_host,
        port=getattr(settings, "DATABASE_PORT", 5432),
        database=getattr(settings, "DATABASE_NAME", "stemcogent"),
        query={"ssl": getattr(settings, "DATABASE_SSL_MODE", "require")},
    ).render_as_string(hide_password=False)
def _database_url() -> str | None:
    """Backward-compatible alias for callers predating the migration runtime."""
    return get_database_url()


def get_engine() -> AsyncEngine | None:
    global _engine, _session_factory

    if _engine is None:
        database_url = get_database_url()
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
        logger.exception("PostgreSQL readiness check failed")
        return "unavailable"

    return "ok"


async def close_database_connection() -> None:
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
