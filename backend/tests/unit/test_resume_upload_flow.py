"""End-to-end tests for resume upload/list/fetch."""

import io
import pytest
from docx import Document
from fastapi.testclient import TestClient

import app.services.resume_service as resume_service_module
from app.services.storage.local import LocalStorageBackend


@pytest.fixture(autouse=True)
def isolate_storage(monkeypatch, tmp_path):
    backend = LocalStorageBackend(base_dir=tmp_path)
    monkeypatch.setattr(resume_service_module, "get_storage_backend", lambda: backend)


def _make_docx_bytes(text: str) -> bytes:
    document = Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _signup_candidate(client: TestClient, email: str = "candidate-upload@example.com") -> str:
    response = client.post("/api/v1/auth/signup", json={
        "email": email, "password": "supersecret123",
        "full_name": "Test Candidate", "role": "candidate",
    })
    return response.json()["access_token"]


@pytest.mark.unit
def test_upload_resume_succeeds_and_returns_parsed_text(client: TestClient) -> None:
    token = _signup_candidate(client)
    docx_bytes = _make_docx_bytes("Experienced Python Developer with FastAPI expertise")
    response = client.post("/api/v1/resumes/upload", headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "resume.docx"
    assert body["file_type"] == "docx"
    assert "Python Developer" in body["parsed_text"]


@pytest.mark.unit
def test_upload_rejects_disallowed_extension(client: TestClient) -> None:
    token = _signup_candidate(client)
    response = client.post("/api/v1/resumes/upload", headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.txt", b"plain text resume", "text/plain")})
    assert response.status_code == 400


@pytest.mark.unit
def test_upload_extracts_skills_experience_and_education(client: TestClient, db_session) -> None:
    from app.models.skill import Skill
    db_session.add(Skill(name="Python", category="Programming Language"))
    db_session.commit()

    token = _signup_candidate(client, "extraction-test@example.com")
    resume_text = ("Senior Software Engineer with 6 years of experience. "
                    "Strong Python developer. Bachelor's degree in Computer Science.")
    docx_bytes = _make_docx_bytes(resume_text)
    response = client.post("/api/v1/resumes/upload", headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.docx", docx_bytes, "application/octet-stream")})

    assert response.status_code == 201
    body = response.json()
    assert "Python" in body["extracted_skills"]
    assert body["years_experience"] == 6.0
    assert body["education_level"] == "bachelor"


@pytest.mark.unit
def test_upload_generates_embedding(client: TestClient, db_session) -> None:
    """
    Milestone 6: confirms an embedding was actually computed and stored
    for the uploaded resume -- checked via direct DB query since
    `ResumeRead` deliberately doesn't expose the raw vector in the API
    response (a client has no use for 384 raw floats).
    """
    from app.models.resume import Resume

    token = _signup_candidate(client, "embedding-test@example.com")
    docx_bytes = _make_docx_bytes("Backend engineer with cloud infrastructure experience")
    response = client.post("/api/v1/resumes/upload", headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.docx", docx_bytes, "application/octet-stream")})
    assert response.status_code == 201

    resume_id = response.json()["id"]
    resume = db_session.get(Resume, resume_id)
    assert resume.embedding is not None
    assert len(resume.embedding) == 384


@pytest.mark.unit
def test_upload_requires_authentication(client: TestClient) -> None:
    docx_bytes = _make_docx_bytes("Some content")
    response = client.post("/api/v1/resumes/upload",
        files={"file": ("resume.docx", docx_bytes, "application/octet-stream")})
    assert response.status_code == 401


@pytest.mark.unit
def test_recruiter_cannot_upload_resume(client: TestClient) -> None:
    signup = client.post("/api/v1/auth/signup", json={
        "email": "recruiter-upload-test@example.com", "password": "supersecret123",
        "full_name": "Test Recruiter", "role": "recruiter",
    })
    token = signup.json()["access_token"]
    docx_bytes = _make_docx_bytes("Some content")
    response = client.post("/api/v1/resumes/upload", headers={"Authorization": f"Bearer {token}"},
        files={"file": ("resume.docx", docx_bytes, "application/octet-stream")})
    assert response.status_code == 403


@pytest.mark.unit
def test_list_resumes_returns_only_own_resumes(client: TestClient) -> None:
    token_a = _signup_candidate(client, "candidate-a@example.com")
    token_b = _signup_candidate(client, "candidate-b@example.com")
    client.post("/api/v1/resumes/upload", headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("a.docx", _make_docx_bytes("Candidate A resume"), "application/octet-stream")})
    response = client.get("/api/v1/resumes/", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.unit
def test_get_resume_owned_by_another_candidate_returns_404(client: TestClient) -> None:
    token_a = _signup_candidate(client, "owner@example.com")
    token_b = _signup_candidate(client, "intruder@example.com")
    upload_response = client.post("/api/v1/resumes/upload", headers={"Authorization": f"Bearer {token_a}"},
        files={"file": ("owner.docx", _make_docx_bytes("Owner's resume"), "application/octet-stream")})
    resume_id = upload_response.json()["id"]
    response = client.get(f"/api/v1/resumes/{resume_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert response.status_code == 404
