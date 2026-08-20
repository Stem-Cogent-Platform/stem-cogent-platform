from unittest.mock import AsyncMock

from app.workers import runtime


def test_worker_runtime_closes_loop_bound_clients(monkeypatch) -> None:
    close_database = AsyncMock()
    close_redis = AsyncMock()
    monkeypatch.setattr(runtime, "close_database_connection", close_database)
    monkeypatch.setattr(runtime, "close_redis_connection", close_redis)

    async def operation() -> str:
        return "ok"

    assert runtime.run_async_worker(operation) == "ok"
    close_database.assert_awaited_once()
    close_redis.assert_awaited_once()


def test_worker_runtime_closes_clients_after_failure(monkeypatch) -> None:
    close_database = AsyncMock()
    close_redis = AsyncMock()
    monkeypatch.setattr(runtime, "close_database_connection", close_database)
    monkeypatch.setattr(runtime, "close_redis_connection", close_redis)

    async def operation() -> str:
        raise RuntimeError("boom")

    try:
        runtime.run_async_worker(operation)
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("worker exception was not propagated")
    close_database.assert_awaited_once()
    close_redis.assert_awaited_once()
