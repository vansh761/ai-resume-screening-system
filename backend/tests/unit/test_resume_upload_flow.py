"""
End-to-end tests for resume upload/list/fetch, exercised through real
HTTP requests (signup -> upload -> retrieve), the same style used for
the Milestone 3 auth flow tests.

Storage is redirected to a pytest `tmp_path` via monkeypatching the
`get_storage_backend` reference used inside `resume_service` -- this
keeps tests from writing real files into the container's actual
`uploads/` directory, the same isolation principle as swapping
Postgres for SQLite in `conftest.py`.
"""

import io

import pytest
from docx import Document
from fastapi.testclient import TestClient

import app.services.resume_service as resume_service_module
from app.services.storage.local import LocalStorageBackend


@pytest.fixture(autouse=True)
def isolate_storage(monkeypatch, tmp_path):
    """Redirects all resume storage in this test file to a temp directory."""
    backend = LocalStorageBackend(base_dir=tmp_path)
    monkeypatch.setattr(resume_service_module, "get_storage_backend", lambda: backend)


def _make_docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _signup_candidate(client: TestClient, email: str = "candidate-upload@example.com") -> str:
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": email,
            "password": "supersecret123",
            "full_name": "Test Candidate",
            "role": "candidate",
        },
    )
    return response.json()["access_token"]


@pytest.mark.unit
def test_upload_resume_succeeds_and_returns_parsed_text(client: TestClient) -> None:
    token = _signup_candidate(client)
    docx_bytes = _make_docx_bytes("Experienced Python Developer with FastAPI expertise")

    response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "resume.docx"
    assert body["file_type"] == "docx"
    assert "Python Developer" in body["parsed_text"]


@pytest.mark.unit
def test_upload_rejects_disallowed_extension(client: TestClient) -> None:
    token = _signup_candidate(client)

    response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.txt", b"plain text resume", "text/plain")},
    )

    assert response.status_code == 400


@pytest.mark.unit
def test_upload_extracts_skills_experience_and_education(client: TestClient, db_session) -> None:
    """
    End-to-end proof that Milestone 5's extraction pipeline actually
    runs as part of upload: seeds a known skill directly into the test
    DB, uploads a resume mentioning it plus an experience figure and a
    degree, and checks all three land in the API response.
    """
    from app.models.skill import Skill

    db_session.add(Skill(name="Python", category="Programming Language"))
    db_session.commit()

    token = _signup_candidate(client, "extraction-test@example.com")
    resume_text = (
        "Senior Software Engineer with 6 years of experience. "
        "Strong Python developer. Bachelor's degree in Computer Science."
    )
    docx_bytes = _make_docx_bytes(resume_text)

    response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.docx", docx_bytes, "application/octet-stream")},
    )

    assert response.status_code == 201
    body = response.json()
    assert "Python" in body["extracted_skills"]
    assert body["years_experience"] == 6.0
    assert body["education_level"] == "bachelor"


@pytest.mark.unit
def test_upload_requires_authentication(client: TestClient) -> None:
    docx_bytes = _make_docx_bytes("Some content")
    response = client.post(
        "/api/v1/resumes/upload",
        files={"file": ("resume.docx", docx_bytes, "application/octet-stream")},
    )
    assert response.status_code == 401


@pytest.mark.unit
def test_recruiter_cannot_upload_resume(client: TestClient) -> None:
    """Uploading a resume is a candidate-only action."""
    signup = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "recruiter-upload-test@example.com",
            "password": "supersecret123",
            "full_name": "Test Recruiter",
            "role": "recruiter",
        },
    )
    token = signup.json()["access_token"]

    docx_bytes = _make_docx_bytes("Some content")
    response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.docx", docx_bytes, "application/octet-stream")},
    )
    assert response.status_code == 403


@pytest.mark.unit
def test_list_resumes_returns_only_own_resumes(client: TestClient) -> None:
    token_a = _signup_candidate(client, "candidate-a@example.com")
    token_b = _signup_candidate(client, "candidate-b@example.com")

    client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("a.docx", _make_docx_bytes("Candidate A resume"), "application/octet-stream")},
    )

    response = client.get("/api/v1/resumes/", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 200
    assert response.json() == []  # candidate B has uploaded nothing


@pytest.mark.unit
def test_get_resume_owned_by_another_candidate_returns_404(client: TestClient) -> None:
    token_a = _signup_candidate(client, "owner@example.com")
    token_b = _signup_candidate(client, "intruder@example.com")

    upload_response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("owner.docx", _make_docx_bytes("Owner's resume"), "application/octet-stream")},
    )
    resume_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/resumes/{resume_id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert response.status_code == 404
