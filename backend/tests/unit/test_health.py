from fastapi.testclient import TestClient
import pytest

from app.main import create_application


@pytest.mark.unit
def test_health_check_returns_ok() -> None:
    app = create_application()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "environment" in body
