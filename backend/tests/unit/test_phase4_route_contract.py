from fastapi.testclient import TestClient

from app.main import app


def test_phase4_product_routes_use_canonical_api_base() -> None:
    client = TestClient(app)
    paths = set(client.get("/api/v1/openapi.json").json()["paths"])

    assert "/api/v1/context/company" in paths
    assert "/api/v1/me/decision-lens" in paths
    assert "/api/v1/me/focus-areas" in paths
    assert "/api/v1/company/briefs" in paths
    assert "/api/v1/signals" in paths
    assert "/api/v1/watchlist" in paths
    assert "/api/v1/team" in paths
    assert "/api/v1/integrations" in paths


def test_canonical_product_routes_reach_authentication_boundary() -> None:
    client = TestClient(app)

    for path in (
        "/api/v1/briefs",
        "/api/v1/company/briefs",
        "/api/v1/signals",
        "/api/v1/watchlist",
        "/api/v1/context/company",
        "/api/v1/me/decision-lens",
    ):
        response = client.get(path)
        assert response.status_code == 401, (path, response.text)
        assert response.json()["detail"] == "Bearer token required"
