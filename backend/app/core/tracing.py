"""AWS X-Ray instrumentation for the FastAPI ASGI lifecycle."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aws_xray_sdk.core import patch_all, xray_recorder
from aws_xray_sdk.core.async_context import AsyncContext
from aws_xray_sdk.core.models.trace_header import TraceHeader
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import correlation_id_var, get_logger

logger = get_logger(__name__)


class XRayASGIMiddleware:
    """Create and close one X-Ray segment for each HTTP request."""

    def __init__(self, app: Callable[..., Awaitable[None]]) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[..., Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        trace_header = TraceHeader.from_header_str(
            headers.get(b"x-amzn-trace-id", b"").decode("latin-1")
        )
        path = scope.get("path", "/")
        sampling = 1 if path.startswith("/health/") else trace_header.sampled
        segment = xray_recorder.begin_segment(
            get_settings().SERVICE_NAME,
            traceid=trace_header.root,
            parent_id=trace_header.parent,
            sampling=sampling,
        )
        segment.put_http_meta("method", scope.get("method"))
        segment.put_http_meta("url", path)
        correlation_id = (
            headers.get(b"x-correlation-id", b"").decode("latin-1")
            or correlation_id_var.get()
        )
        if correlation_id:
            segment.put_annotation("correlation_id", correlation_id)
        status_code = 500

        async def traced_send(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, traced_send)
        except Exception as exc:
            segment.add_exception(exc, exc.__traceback__)
            raise
        finally:
            segment.put_http_meta("status", status_code)
            # Starlette's BaseHTTPMiddleware executes the inner application in
            # a child task, which can clear the SDK's task-local entity. Put
            # the original segment back before closing so it is always sent.
            xray_recorder.context.put_segment(segment)
            xray_recorder.end_segment()


def configure_tracing(app: FastAPI) -> None:
    """Enable X-Ray only where the runtime explicitly opts in."""

    settings = get_settings()
    if not settings.XRAY_ENABLED:
        logger.info("AWS X-Ray tracing disabled")
        return

    xray_recorder.configure(
        service=settings.SERVICE_NAME,
        context=AsyncContext(),
        context_missing="LOG_ERROR",
        daemon_address=settings.XRAY_DAEMON_ADDRESS,
    )
    patch_all()
    app.add_middleware(XRayASGIMiddleware)
    logger.info("AWS X-Ray tracing enabled")
