from unittest.mock import AsyncMock

from app.api.v1 import health
from app.main import app
from fastapi.testclient import TestClient


def test_liveness_reports_alive() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains; preload"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_readiness_reports_ready_when_dependencies_are_healthy(
    monkeypatch,
) -> None:
    monkeypatch.setattr(health, "check_database_connection", AsyncMock(return_value="ok"))
    monkeypatch.setattr(health, "check_redis_connection", AsyncMock(return_value="ok"))

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {"postgres": "ok", "redis": "ok"},
    }


def test_readiness_reports_unavailable_dependency(monkeypatch) -> None:
    monkeypatch.setattr(
        health,
        "check_database_connection",
        AsyncMock(return_value="unavailable"),
    )
    monkeypatch.setattr(health, "check_redis_connection", AsyncMock(return_value="ok"))

    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "dependencies": {"postgres": "unavailable", "redis": "ok"},
    }
