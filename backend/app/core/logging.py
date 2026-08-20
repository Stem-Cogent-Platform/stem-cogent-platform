"""Structured application and process logging for CloudWatch Logs."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from app.core.config import get_settings

if sys.platform != "win32":
    from gunicorn import glogging

# Context variables propagated through the request and worker lifecycle.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
tenant_id_var: ContextVar[str | None] = ContextVar("tenant_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
event_id_var: ContextVar[str | None] = ContextVar("event_id", default=None)
signal_id_var: ContextVar[str | None] = ContextVar("signal_id", default=None)
brief_id_var: ContextVar[str | None] = ContextVar("brief_id", default=None)

_CONTEXT_VARIABLES = {
    "request_id": request_id_var,
    "correlation_id": correlation_id_var,
    "tenant_id": tenant_id_var,
    "user_id": user_id_var,
    "event_id": event_id_var,
    "signal_id": signal_id_var,
    "brief_id": brief_id_var,
}
_OPTIONAL_RECORD_FIELDS = (
    "duration_ms",
    "status",
    "status_code",
    "error_code",
    "http_method",
    "http_path",
)


class StructuredFormatter(logging.Formatter):
    """Render one stable JSON object per log record."""

    def format(self, record: logging.LogRecord) -> str:
        settings = get_settings()
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).isoformat(
            timespec="milliseconds"
        ).replace("+00:00", "Z")
        log_record: dict[str, Any] = {
            "timestamp": timestamp,
            "level": record.levelname,
            "service": getattr(record, "service", settings.SERVICE_NAME),
            "environment": settings.ENVIRONMENT,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": request_id_var.get(),
            "correlation_id": correlation_id_var.get(),
            "tenant_id": tenant_id_var.get(),
            "user_id": user_id_var.get(),
            "event_id": event_id_var.get(),
            "signal_id": signal_id_var.get(),
            "brief_id": brief_id_var.get(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        for field in _OPTIONAL_RECORD_FIELDS:
            if hasattr(record, field):
                log_record[field] = getattr(record, field)

        return json.dumps(log_record, ensure_ascii=False, default=str)


def configure_logging() -> None:
    """Install one JSON stdout handler for application and ASGI loggers."""

    settings = get_settings()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
        logger.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that inherits the process-wide JSON handler."""

    return logging.getLogger(name)


def bind_log_context(**values: str | None) -> dict[str, Token[str | None]]:
    """Bind known context values and return tokens for deterministic cleanup."""

    return {
        name: variable.set(values[name])
        for name, variable in _CONTEXT_VARIABLES.items()
        if name in values
    }


def reset_log_context(tokens: dict[str, Token[str | None]]) -> None:
    """Restore context values saved by :func:`bind_log_context`."""

    for name, token in reversed(tuple(tokens.items())):
        _CONTEXT_VARIABLES[name].reset(token)


if sys.platform != "win32":

    class StructuredGunicornLogger(glogging.Logger):
        """Apply the same JSON contract to Gunicorn master and access logs."""

        def setup(self, cfg: Any) -> None:
            super().setup(cfg)
            formatter = StructuredFormatter()
            for logger in (self.error_log, self.access_log):
                for handler in logger.handlers:
                    handler.setFormatter(formatter)

else:

    class StructuredGunicornLogger:  # pragma: no cover - Docker runs on Linux.
        """Windows import placeholder for the Linux-only Gunicorn adapter."""
