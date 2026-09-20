"""
End-to-end tests for clustering, duplicate detection, and similar-
resume recommendations, exercised through real HTTP requests.
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


def _upload_resume(client: TestClient, token: str, filename: str, text: str) -> str:
    response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, _make_docx_bytes(text), "application/octet-stream")},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.unit
def test_cluster_applicants_groups_by_similarity(client: TestClient) -> None:
    recruiter_token = _signup(client, "recruiter-cluster@example.com", "recruiter")
    job_response = client.post(
        "/api/v1/jobs/",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"title": "Engineer", "description": "General engineering role, open to many backgrounds."},
    )
    job_id = job_response.json()["id"]
    client.patch(
        f"/api/v1/jobs/{job_id}/status",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"status": "open"},
    )

    # Two backend-leaning candidates, one very different (design) candidate.
    backend_texts = [
        "Backend engineer skilled in Python, FastAPI, PostgreSQL, and REST API design.",
        "Software engineer with Python and FastAPI experience building backend services.",
    ]
    design_text = "Graphic designer with expertise in Photoshop, Illustrator, and brand identity design."

    resume_ids = []
    for i, text in enumerate(backend_texts):
        token = _signup(client, f"backend-candidate-{i}@example.com", "candidate")
        rid = _upload_resume(client, token, f"backend_{i}.docx", text)
        resume_ids.append((token, rid))

    design_token = _signup(client, "design-candidate@example.com", "candidate")
    design_rid = _upload_resume(client, design_token, "design.docx", design_text)
    resume_ids.append((design_token, design_rid))

    for token, rid in resume_ids:
        apply_response = client.post(
            "/api/v1/applications/",
            headers={"Authorization": f"Bearer {token}"},
            json={"job_id": job_id, "resume_id": rid},
        )
        assert apply_response.status_code == 201

    cluster_response = client.get(
        f"/api/v1/analysis/jobs/{job_id}/clusters",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert cluster_response.status_code == 200
    clusters = cluster_response.json()
    assert len(clusters) >= 1
    assert sum(c["size"] for c in clusters) == 3


@pytest.mark.unit
def test_detect_duplicates_flags_near_identical_resumes(client: TestClient) -> None:
    recruiter_token = _signup(client, "recruiter-dup@example.com", "recruiter")

    identical_text = (
        "Experienced backend engineer with 5 years working in Python, "
        "Django, PostgreSQL, and cloud deployment on AWS."
    )
    candidate_a_token = _signup(client, "dup-candidate-a@example.com", "candidate")
    _upload_resume(client, candidate_a_token, "resume_a.docx", identical_text)

    candidate_b_token = _signup(client, "dup-candidate-b@example.com", "candidate")
    _upload_resume(client, candidate_b_token, "resume_b.docx", identical_text)

    response = client.get(
        "/api/v1/analysis/duplicates",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert response.status_code == 200
    duplicates = response.json()
    assert len(duplicates) >= 1
    assert duplicates[0]["similarity"] >= 0.97


@pytest.mark.unit
def test_similar_resumes_excludes_the_query_resume_itself(client: TestClient) -> None:
    recruiter_token = _signup(client, "recruiter-similar@example.com", "recruiter")

    candidate_a_token = _signup(client, "similar-a@example.com", "candidate")
    resume_a_id = _upload_resume(
        client, candidate_a_token, "a.docx",
        "Python backend developer with FastAPI and PostgreSQL experience."
    )

    candidate_b_token = _signup(client, "similar-b@example.com", "candidate")
    _upload_resume(
        client, candidate_b_token, "b.docx",
        "Backend engineer skilled in Python, FastAPI, and database design."
    )

    response = client.get(
        f"/api/v1/analysis/resumes/{resume_a_id}/similar",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert response.status_code == 200
    results = response.json()
    assert all(r["resume_id"] != resume_a_id for r in results)


@pytest.mark.unit
def test_analysis_endpoints_require_recruiter_role(client: TestClient) -> None:
    candidate_token = _signup(client, "candidate-analysis-test@example.com", "candidate")
    response = client.get(
        "/api/v1/analysis/duplicates",
        headers={"Authorization": f"Bearer {candidate_token}"},
    )
    assert response.status_code == 403
