"""
End-to-end test for the complete Milestone 7 flow.
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


def _seed_skill(db_session, name: str):
    from app.models.skill import Skill

    skill = Skill(name=name, category="Programming Language")
    db_session.add(skill)
    db_session.commit()
    return skill


@pytest.mark.unit
def test_full_job_application_scoring_flow(client: TestClient, db_session) -> None:
    _seed_skill(db_session, "Python")
    _seed_skill(db_session, "FastAPI")

    recruiter_token = _signup(client, "recruiter@example.com", "recruiter")
    job_response = client.post(
        "/api/v1/jobs/",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={
            "title": "Backend Engineer",
            "description": "Build and maintain backend services using Python and FastAPI.",
            "min_experience_years": 2,
            "required_skills": ["Python", "FastAPI"],
        },
    )
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]
    assert job_response.json()["status"] == "draft"

    open_response = client.patch(
        f"/api/v1/jobs/{job_id}/status",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"status": "open"},
    )
    assert open_response.status_code == 200
    assert open_response.json()["status"] == "open"

    candidate_token = _signup(client, "candidate@example.com", "candidate")
    resume_response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {candidate_token}"},
        files={
            "file": (
                "resume.docx",
                _make_docx_bytes(
                    "Backend engineer with 4 years of experience. "
                    "Skilled in Python and FastAPI development."
                ),
                "application/octet-stream",
            )
        },
    )
    assert resume_response.status_code == 201
    resume_id = resume_response.json()["id"]
    assert set(resume_response.json()["extracted_skills"]) == {"Python", "FastAPI"}

    list_response = client.get("/api/v1/jobs/", headers={"Authorization": f"Bearer {candidate_token}"})
    assert list_response.status_code == 200
    assert any(j["id"] == job_id for j in list_response.json())

    apply_response = client.post(
        "/api/v1/applications/",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"job_id": job_id, "resume_id": resume_id},
    )
    assert apply_response.status_code == 201
    application = apply_response.json()
    assert application["score"] is not None
    assert application["score"]["skills_match_score"] == 100.0
    assert application["score"]["experience_match_score"] == 100.0
    assert "explanation" in application["score"]
    assert application["score"]["explanation"]["skills_match"]["missing_required_skills"] == []

    duplicate_response = client.post(
        "/api/v1/applications/",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"job_id": job_id, "resume_id": resume_id},
    )
    assert duplicate_response.status_code == 409

    ranked_response = client.get(
        f"/api/v1/applications/for-job/{job_id}",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert ranked_response.status_code == 200
    assert len(ranked_response.json()) == 1
    assert ranked_response.json()[0]["score"]["overall_score"] > 0


@pytest.mark.unit
def test_candidate_cannot_see_draft_jobs(client: TestClient) -> None:
    recruiter_token = _signup(client, "recruiter-draft@example.com", "recruiter")
    job_response = client.post(
        "/api/v1/jobs/",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"title": "Unlisted Role", "description": "Not yet open to applicants."},
    )
    job_id = job_response.json()["id"]

    candidate_token = _signup(client, "candidate-draft@example.com", "candidate")
    response = client.get(
        f"/api/v1/jobs/{job_id}", headers={"Authorization": f"Bearer {candidate_token}"}
    )
    assert response.status_code == 404


@pytest.mark.unit
def test_candidate_cannot_apply_with_someone_elses_resume(client: TestClient) -> None:
    recruiter_token = _signup(client, "recruiter-x@example.com", "recruiter")
    job_response = client.post(
        "/api/v1/jobs/",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"title": "Role X", "description": "A role that exists for this test."},
    )
    job_id = job_response.json()["id"]
    client.patch(
        f"/api/v1/jobs/{job_id}/status",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"status": "open"},
    )

    owner_token = _signup(client, "resume-owner@example.com", "candidate")
    resume_response = client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {owner_token}"},
        files={"file": ("r.docx", _make_docx_bytes("Some resume content"), "application/octet-stream")},
    )
    resume_id = resume_response.json()["id"]

    intruder_token = _signup(client, "intruder@example.com", "candidate")
    response = client.post(
        "/api/v1/applications/",
        headers={"Authorization": f"Bearer {intruder_token}"},
        json={"job_id": job_id, "resume_id": resume_id},
    )
    assert response.status_code == 404
