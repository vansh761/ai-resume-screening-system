"""
End-to-end tests for the auth flow, exercised through real HTTP
requests (via FastAPI's TestClient) rather than calling service
functions directly — this is what actually proves the router, the
dependency injection wiring, and the service layer all work together
correctly, not just each piece in isolation.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit
def test_signup_returns_access_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "candidate@example.com",
            "password": "supersecret123",
            "full_name": "Cal Candidate",
            "role": "candidate",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.unit
def test_signup_rejects_duplicate_email(client: TestClient) -> None:
    payload = {
        "email": "dupe@example.com",
        "password": "supersecret123",
        "full_name": "First User",
        "role": "candidate",
    }
    first = client.post("/api/v1/auth/signup", json=payload)
    assert first.status_code == 201

    second = client.post("/api/v1/auth/signup", json=payload)
    assert second.status_code == 409


@pytest.mark.unit
def test_login_with_correct_credentials_succeeds(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/signup",
        json={
            "email": "login-test@example.com",
            "password": "correcthorse",
            "full_name": "Login Tester",
            "role": "recruiter",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "login-test@example.com", "password": "correcthorse"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.unit
def test_login_with_wrong_password_returns_401(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/signup",
        json={
            "email": "wrongpass@example.com",
            "password": "correctpassword",
            "full_name": "Test User",
            "role": "candidate",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpass@example.com", "password": "totally-wrong"},
    )
    assert response.status_code == 401


@pytest.mark.unit
def test_protected_route_requires_token(client: TestClient) -> None:
    """No Authorization header at all → 401, before any role logic runs."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.unit
def test_protected_route_returns_current_user_with_valid_token(client: TestClient) -> None:
    signup_response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "me-test@example.com",
            "password": "supersecret123",
            "full_name": "Me Tester",
            "role": "candidate",
        },
    )
    token = signup_response.json()["access_token"]

    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me-test@example.com"


@pytest.mark.unit
def test_role_gated_route_rejects_wrong_role(client: TestClient) -> None:
    """
    A candidate's perfectly valid token should still get 403 on a
    recruiter-only route — this is the core RBAC guarantee: a valid
    token alone is not sufficient authorization.
    """
    signup_response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "candidate-rbac@example.com",
            "password": "supersecret123",
            "full_name": "Candidate RBAC",
            "role": "candidate",
        },
    )
    token = signup_response.json()["access_token"]

    response = client.get(
        "/api/v1/users/recruiter-only-example",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.unit
def test_role_gated_route_accepts_correct_role(client: TestClient) -> None:
    signup_response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "recruiter-rbac@example.com",
            "password": "supersecret123",
            "full_name": "Recruiter RBAC",
            "role": "recruiter",
        },
    )
    token = signup_response.json()["access_token"]

    response = client.get(
        "/api/v1/users/recruiter-only-example",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
