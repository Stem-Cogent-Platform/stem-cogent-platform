from fastapi.testclient import TestClient

from app.main import app


def test_readiness_checks_postgres_and_redis_services() -> None:
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {"postgres": "ok", "redis": "ok"},
    }
