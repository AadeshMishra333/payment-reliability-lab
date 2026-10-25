from fastapi.testclient import TestClient

from app.main import app


def test_app_starts_and_exposes_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mode": "synthetic-demo"}
