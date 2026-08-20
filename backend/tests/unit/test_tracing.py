from typing import Any

import pytest

from app.core import tracing


class FakeSegment:
    sampled = True

    def __init__(self) -> None:
        self.closed = False
        self.http: dict[str, Any] = {}
        self.annotations: dict[str, str] = {}

    def put_http_meta(self, key: str, value: Any) -> None:
        self.http[key] = value

    def put_annotation(self, key: str, value: str) -> None:
        self.annotations[key] = value

    def add_exception(self, *_: Any) -> None:
        raise AssertionError("The successful request must not record an exception")

    def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_xray_middleware_closes_and_emits_health_segment(monkeypatch) -> None:
    segment = FakeSegment()
    emitted: list[FakeSegment] = []
    monkeypatch.setattr(tracing.xray_recorder, "begin_segment", lambda *args, **kwargs: segment)
    monkeypatch.setattr(
        tracing.xray_recorder,
        "emitter",
        type("Emitter", (), {"send_entity": lambda self, entity: emitted.append(entity)})(),
    )

    async def inner(scope, receive, send) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    messages: list[dict[str, Any]] = []

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b""}

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    middleware = tracing.XRayASGIMiddleware(inner)
    await middleware(
        {
            "type": "http",
            "method": "GET",
            "path": "/health/live",
            "headers": [(b"x-correlation-id", b"correlation-1")],
        },
        receive,
        send,
    )

    assert messages[0]["status"] == 200
    assert segment.closed
    assert emitted == [segment]
    assert segment.http == {"method": "GET", "url": "/health/live", "status": 200}
    assert segment.annotations == {"correlation_id": "correlation-1"}
