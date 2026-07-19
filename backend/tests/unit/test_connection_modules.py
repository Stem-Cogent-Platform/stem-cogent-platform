import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.core import database, redis


def test_database_url_converts_postgres_scheme(monkeypatch) -> None:
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: SimpleNamespace(DATABASE_URL="postgresql://user:pass@db/app"),
    )

    assert database._database_url() == "postgresql+asyncpg://user:pass@db/app"


def test_database_url_is_none_when_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(database, "get_settings", lambda: SimpleNamespace(DATABASE_URL=None))

    assert database._database_url() is None


def test_database_session_requires_configuration(monkeypatch) -> None:
    monkeypatch.setattr(database, "_engine", None)
    monkeypatch.setattr(database, "_session_factory", None)
    monkeypatch.setattr(database, "get_engine", lambda: None)

    async def get_session() -> None:
        with pytest.raises(RuntimeError, match="not configured"):
            await anext(database.get_session())

    asyncio.run(get_session())


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
        lambda: SimpleNamespace(REDIS_URL=None, REDIS_HOST="cache", REDIS_PORT=6380),
    )

    assert redis._redis_url() == "redis://cache:6380/0"


def test_redis_url_is_none_when_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(
        redis,
        "get_settings",
        lambda: SimpleNamespace(REDIS_URL=None, REDIS_HOST=None),
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
