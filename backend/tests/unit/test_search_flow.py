"""
End-to-end test for semantic search, exercised through real HTTP
requests: upload two very different resumes as two different
candidates, then confirm a recruiter's job-description search actually
ranks the more relevant resume first. This is the test that proves
Milestone 6's entire pipeline — embedding generation, storage, FAISS
index assembly, and ranking — works together correctly, not just each
piece in isolation.
"""

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


def _signup(client: TestClient, email: str, role: str) -> str:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "supersecret123", "full_name": "Test User", "role": role},
    )
    return response.json()["access_token"]


@pytest.mark.unit
def test_search_ranks_relevant_resume_above_irrelevant_one(client: TestClient) -> None:
    backend_token = _signup(client, "backend-candidate@example.com", "candidate")
    client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {backend_token}"},
        files={
            "file": (
                "backend_resume.docx",
                _make_docx_bytes(
                    "Senior backend engineer with extensive experience building "
                    "REST APIs, working with PostgreSQL databases, and deploying "
                    "microservices on cloud infrastructure."
                ),
                "application/octet-stream",
            )
        },
    )

    chef_token = _signup(client, "chef-candidate@example.com", "candidate")
    client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {chef_token}"},
        files={
            "file": (
                "chef_resume.docx",
                _make_docx_bytes(
                    "Professional pastry chef with a decade of experience in "
                    "French cuisine, menu design, and kitchen management."
                ),
                "application/octet-stream",
            )
        },
    )

    recruiter_token = _signup(client, "recruiter-search@example.com", "recruiter")
    response = client.post(
        "/api/v1/search/resumes",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={
            "job_description": "Looking for a backend software engineer with API and database experience",
            "top_k": 5,
        },
    )

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    # The backend-relevant resume should rank first, with a
    # meaningfully higher similarity score than the unrelated one.
    assert results[0]["original_filename"] == "backend_resume.docx"
    assert results[0]["similarity_score"] > results[1]["similarity_score"]


@pytest.mark.unit
def test_search_requires_recruiter_role(client: TestClient) -> None:
    candidate_token = _signup(client, "candidate-search-test@example.com", "candidate")
    response = client.post(
        "/api/v1/search/resumes",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"job_description": "Looking for a backend engineer", "top_k": 5},
    )
    assert response.status_code == 403


@pytest.mark.unit
def test_search_with_no_resumes_returns_empty_list(client: TestClient) -> None:
    recruiter_token = _signup(client, "recruiter-empty-search@example.com", "recruiter")
    response = client.post(
        "/api/v1/search/resumes",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"job_description": "Any job description at all", "top_k": 5},
    )
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.unit
def test_search_rejects_too_short_job_description(client: TestClient) -> None:
    recruiter_token = _signup(client, "recruiter-validation-test@example.com", "recruiter")
    response = client.post(
        "/api/v1/search/resumes",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"job_description": "short", "top_k": 5},
    )
    assert response.status_code == 422
