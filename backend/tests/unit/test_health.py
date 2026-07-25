"""Health endpoint tests without database dependency."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_envelope() -> None:
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["error"] is None
    assert "request_id" in body
    assert response.headers.get("X-Request-ID")
