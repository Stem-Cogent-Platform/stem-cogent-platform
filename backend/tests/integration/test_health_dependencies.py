from time import sleep

from fastapi.testclient import TestClient

from app.main import app


def test_readiness_checks_postgres_and_redis_services() -> None:
    with TestClient(app) as client:
        for _ in range(15):
            response = client.get("/health/ready")
            if response.status_code == 200:
                break
            sleep(1)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "ready",
        "dependencies": {"postgres": "ok", "redis": "ok"},
    }
