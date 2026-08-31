import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core import database, redis


def test_database_url_converts_postgres_scheme(monkeypatch) -> None:
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: SimpleNamespace(DATABASE_URL="postgresql://example.invalid/app"),
    )

    assert database._database_url() == "postgresql+asyncpg://example.invalid/app"


def test_database_url_is_none_when_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: SimpleNamespace(
            DATABASE_URL=None, DATABASE_CREDENTIALS_ARN=None, DATABASE_HOST=None
        ),
    )

    assert database._database_url() is None


def test_database_url_resolves_managed_credentials(monkeypatch) -> None:
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: SimpleNamespace(
            DATABASE_URL=None,
            DATABASE_CREDENTIALS_ARN="arn:aws:secretsmanager:eu-west-1:123456789012:secret:database",
            DATABASE_HOST="database.internal",
            DATABASE_PORT=5432,
            DATABASE_NAME="stemcogent",
            DATABASE_SSL_MODE="require",
        ),
    )
    monkeypatch.setattr(
        database,
        "get_json_secret",
        lambda _arn: {"username": "app_user", "password": "p@ss/word"},
    )

    assert database._database_url() == (
        "postgresql+asyncpg://app_user:p%40ss%2Fword@database.internal:5432/stemcogent?ssl=require"
    )


def test_database_session_requires_configuration(monkeypatch) -> None:
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "_session_factory", None)
    monkeypatch.setattr(database, "get_engine", lambda: None)

    async def get_session() -> None:
        with pytest.raises(RuntimeError, match="not configured"):
            await anext(database.get_session())

    asyncio.run(get_session())


def test_database_engine_uses_bounded_production_pool(monkeypatch) -> None:
    engine = object()
    create_engine = Mock(return_value=engine)
    session_maker = Mock()
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "_session_factory", None)
    monkeypatch.setattr(database, "create_async_engine", create_engine)
    monkeypatch.setattr(database, "async_sessionmaker", session_maker)
    monkeypatch.setattr(
        database, "get_database_url", lambda: "postgresql+asyncpg://db/app"
    )
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: SimpleNamespace(
            DATABASE_POOL_SIZE=3,
            DATABASE_MAX_OVERFLOW=2,
            DATABASE_POOL_TIMEOUT_SECONDS=10,
            DATABASE_POOL_RECYCLE_SECONDS=300,
        ),
    )

    assert database.get_engine() is engine
    create_engine.assert_called_once_with(
        "postgresql+asyncpg://db/app",
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        pool_timeout=10,
        pool_recycle=300,
    )
    session_maker.assert_called_once_with(engine, expire_on_commit=False)


def test_database_health_is_not_configured_without_engine(monkeypatch) -> None:
    monkeypatch.setattr(database, "get_engine", lambda: None)

    assert asyncio.run(database.check_database_connection()) == "not_configured"


def test_close_database_resets_connection_state(monkeypatch) -> None:
    engine = SimpleNamespace(dispose=AsyncMock())
    monkeypatch.setattr(database, "_engine", engine)
    monkeypatch.setattr(database, "_session_factory", Mock())

    asyncio.run(database.close_database_connection())

    engine.dispose.assert_awaited_once()
    assert database._engine is None
    assert database._session_factory is None


def test_redis_url_uses_explicit_url(monkeypatch) -> None:
    monkeypatch.setattr(
        redis,
        "get_settings",
        lambda: SimpleNamespace(REDIS_URL="redis://cache:6379/1", REDIS_HOST=None),
    )

    assert redis._redis_url() == "redis://cache:6379/1"


def test_redis_url_uses_host_and_port(monkeypatch) -> None:
    monkeypatch.setattr(
        redis,
        "get_settings",
        lambda: SimpleNamespace(
            REDIS_URL=None,
            REDIS_HOST="cache",
            REDIS_PORT=6380,
            REDIS_AUTH_TOKEN_ARN="arn:aws:secretsmanager:eu-west-1:123456789012:secret:redis",
            REDIS_TLS_ENABLED=True,
        ),
    )
    monkeypatch.setattr(redis, "get_secret_string", lambda _arn: "token/value")

    assert (
        redis._redis_url()
        == "rediss://:token%2Fvalue@cache:6380/0?ssl_cert_reqs=required"
    )


def test_redis_url_is_none_when_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(
        redis,
        "get_settings",
        lambda: SimpleNamespace(
            REDIS_URL=None, REDIS_HOST=None, REDIS_AUTH_TOKEN_ARN=None
        ),
    )

    assert redis._redis_url() is None


def test_redis_health_is_not_configured_without_client(monkeypatch) -> None:
    monkeypatch.setattr(redis, "get_redis_client", lambda: None)

    assert asyncio.run(redis.check_redis_connection()) == "not_configured"


def test_close_redis_resets_connection_state(monkeypatch) -> None:
    client = SimpleNamespace(aclose=AsyncMock())
    monkeypatch.setattr(redis, "_client", client)

    asyncio.run(redis.close_redis_connection())

    client.aclose.assert_awaited_once()
    assert redis._client is None
