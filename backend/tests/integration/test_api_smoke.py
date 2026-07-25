"""Local API smoke tests that do not require PostgreSQL/Docker."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


REQUIRED_OPENAPI_PATHS = {
    "/api/v1/setup/status",
    "/api/v1/auth/login",
    "/api/v1/draws",
    "/api/v1/analytics/overview",
    "/api/v1/recommendations",
    "/api/v1/backtests",
    "/api/v1/strategies",
    "/api/v1/settings/ai",
    "/api/v1/settings/system",
    "/api/v1/system/jobs",
}


def test_health_and_openapi_surface() -> None:
    app = create_app()
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["error"] is None
    assert body.get("request_id")
    assert health.headers.get("X-Request-ID")

    openapi = client.get("/api/openapi.json")
    assert openapi.status_code == 200
    paths = set(openapi.json().get("paths", {}))
    missing = sorted(REQUIRED_OPENAPI_PATHS - paths)
    assert not missing, f"missing openapi paths: {missing}"


def test_spa_index_served_when_frontend_dist_present() -> None:
    app = create_app()
    client = TestClient(app)
    # Repo frontend/dist is preferred by create_app candidates when present.
    res = client.get("/")
    # Either SPA HTML (200) or API-less redirect/404 depending on dist presence.
    assert res.status_code in {200, 404}
    if res.status_code == 200:
        text = res.text.lower()
        assert "<html" in text or "<!doctype html" in text
