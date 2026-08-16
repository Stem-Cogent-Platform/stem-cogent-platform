import io
import json
import logging

from fastapi.testclient import TestClient

from app.core.logging import (
    StructuredFormatter,
    bind_log_context,
    reset_log_context,
)
from app.main import app


def test_structured_formatter_emits_json_and_context() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("tests.structured")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    tokens = bind_log_context(request_id="req-1", correlation_id="corr-1")

    try:
        logger.info("request complete", extra={"duration_ms": 12.5, "status_code": 200})
    finally:
        reset_log_context(tokens)

    record = json.loads(stream.getvalue())
    assert record["message"] == "request complete"
    assert record["request_id"] == "req-1"
    assert record["correlation_id"] == "corr-1"
    assert record["duration_ms"] == 12.5
    assert record["status_code"] == 200
    assert record["timestamp"].endswith("Z")


def test_structured_formatter_serializes_exceptions() -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(StructuredFormatter())
    logger = logging.getLogger("tests.exception")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.ERROR)

    try:
        raise RuntimeError("expected test failure")
    except RuntimeError:
        logger.exception("operation failed", extra={"error_code": "TEST_FAILURE"})

    record = json.loads(stream.getvalue())
    assert record["error_code"] == "TEST_FAILURE"
    assert "RuntimeError: expected test failure" in record["exception"]


def test_request_middleware_propagates_correlation_headers() -> None:
    output = io.StringIO()
    root_handler = logging.getLogger().handlers[0]
    original_stream = root_handler.setStream(output)
    try:
        with TestClient(app) as client:
            response = client.get(
                "/health/live",
                headers={"X-Request-ID": "request-123", "X-Correlation-ID": "correlation-456"},
            )
    finally:
        root_handler.setStream(original_stream)

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "request-123"
    assert response.headers["x-correlation-id"] == "correlation-456"

    records = [json.loads(line) for line in output.getvalue().splitlines() if line]
    request_record = next(record for record in records if record["message"] == "HTTP request completed")
    assert request_record["request_id"] == "request-123"
    assert request_record["correlation_id"] == "correlation-456"
    assert request_record["status_code"] == 200


def test_request_middleware_generates_identifiers() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live", headers={"X-Request-ID": "\n"})

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.headers["x-request-id"] != "\n"
    assert response.headers["x-correlation-id"] == response.headers["x-request-id"]
