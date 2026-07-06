"""
Smoke test for application health.

This is intentionally the first test in the repo. Before testing any
business logic, we verify the app can even boot and respond — this is
what CI's very first pipeline stage will check.
"""

from fastapi.testclient import TestClient
import pytest

from app.main import create_application


@pytest.mark.unit
def test_health_check_returns_ok() -> None:
    """The /health endpoint should return 200 with status 'ok'."""
    app = create_application()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "environment" in body
