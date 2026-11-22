"""
Tests for Milestone 10: asynchronous resume processing.

Service-level tests call `process_resume` directly (what a Celery
worker does); endpoint-level tests use the `client` fixture, whose
inline dispatcher runs the same pipeline before the request returns.
Where a test needs to observe the PENDING state, it replaces the
dispatcher with a no-op and runs `process_resume` by hand afterwards,
which is a faithful simulation of "the worker hasn't picked it up yet".
"""

import io
import uuid

import pytest
from docx import Document
from fastapi.testclient import TestClient
from sqlalchemy import func, select

import app.services.resume_service as resume_service_module
from app.models.resume import FileType, ProcessingStatus, Resume
from app.models.skill import ResumeSkill, Skill
from app.models.user import User, UserRole
from app.services.resume_processing_service import process_resume
from app.services.storage.local import LocalStorageBackend


@pytest.fixture()
def storage(monkeypatch, tmp_path) -> LocalStorageBackend:
    backend = LocalStorageBackend(base_dir=tmp_path)
    monkeypatch.setattr(resume_service_module, "get_storage_backend", lambda: backend)
    return backend


def _docx_bytes(text: str) -> bytes:
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


def _make_pending_resume(db_session, storage, content: bytes, filename: str = "r.docx") -> Resume:
    candidate = User(
        email=f"c-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x",
        full_name="Test Candidate",
        role=UserRole.CANDIDATE,
    )
    db_session.add(candidate)
    db_session.commit()

    key = f"{candidate.id}/{uuid.uuid4().hex}_{filename}"
    storage.save(content, key)
    resume = Resume(
        candidate_id=candidate.id,
        original_filename=filename,
        storage_path=key,
        file_type=FileType.DOCX,
        processing_status=ProcessingStatus.PENDING,
    )
    db_session.add(resume)
    db_session.commit()
    return resume


def _upload(client: TestClient, token: str, filename: str, content: bytes):
    return client.post(
        "/api/v1/resumes/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, content, "application/octet-stream")},
    )


# --------------------------- service-level ---------------------------


@pytest.mark.unit
def test_process_resume_completes_pending_resume(db_session, storage) -> None:
    db_session.add(Skill(name="Python", category="Programming Language"))
    db_session.commit()
    resume = _make_pending_resume(
        db_session, storage,
        _docx_bytes("Backend engineer with 5 years of experience. Python expert. Bachelor's degree."),
    )

    process_resume(db_session, resume.id, storage=storage)
    db_session.refresh(resume)

    assert resume.processing_status == ProcessingStatus.COMPLETED
    assert "Python" in resume.parsed_text
    assert resume.extracted_years_experience == 5.0
    assert resume.embedding is not None and len(resume.embedding) == 384
    skill_count = db_session.scalar(
        select(func.count()).select_from(ResumeSkill).where(ResumeSkill.resume_id == resume.id)
    )
    assert skill_count == 1


@pytest.mark.unit
def test_process_resume_skips_already_completed_resume(db_session, storage) -> None:
    """A redelivered task for a finished resume must be a no-op (idempotency)."""

    class ExplodingStorage:
        def read(self, key):
            raise AssertionError("storage must not be read for a COMPLETED resume")

    resume = _make_pending_resume(db_session, storage, _docx_bytes("Some content"))
    resume.processing_status = ProcessingStatus.COMPLETED
    db_session.commit()

    process_resume(db_session, resume.id, storage=ExplodingStorage())  # must not raise


@pytest.mark.unit
def test_reprocessing_does_not_duplicate_skills(db_session, storage) -> None:
    """
    Simulates a worker dying after saving skills but before marking the
    resume COMPLETED: the task is redelivered with status still PENDING.
    Without clearing old ResumeSkill rows first, the re-run would hit the
    (resume_id, skill_id) unique constraint.
    """
    db_session.add(Skill(name="Python", category="Programming Language"))
    db_session.commit()
    resume = _make_pending_resume(db_session, storage, _docx_bytes("Python developer"))

    process_resume(db_session, resume.id, storage=storage)
    resume.processing_status = ProcessingStatus.PENDING
    db_session.commit()
    process_resume(db_session, resume.id, storage=storage)  # must not raise

    db_session.refresh(resume)
    skill_count = db_session.scalar(
        select(func.count()).select_from(ResumeSkill).where(ResumeSkill.resume_id == resume.id)
    )
    assert skill_count == 1
    assert resume.processing_status == ProcessingStatus.COMPLETED


@pytest.mark.unit
def test_missing_file_marks_resume_failed(db_session, storage) -> None:
    resume = _make_pending_resume(db_session, storage, _docx_bytes("Some content"))
    storage.delete(resume.storage_path)

    process_resume(db_session, resume.id, storage=storage)
    db_session.refresh(resume)

    assert resume.processing_status == ProcessingStatus.FAILED


@pytest.mark.unit
def test_corrupt_file_marks_resume_failed(db_session, storage) -> None:
    resume = _make_pending_resume(db_session, storage, b"this is not a real docx file")

    process_resume(db_session, resume.id, storage=storage)
    db_session.refresh(resume)

    assert resume.processing_status == ProcessingStatus.FAILED
    assert resume.parsed_text is None


@pytest.mark.unit
def test_process_resume_ignores_nonexistent_resume(db_session, storage) -> None:
    process_resume(db_session, uuid.uuid4(), storage=storage)  # must not raise


# --------------------------- endpoint-level ---------------------------


@pytest.mark.unit
def test_upload_is_pending_until_worker_runs(client: TestClient, db_session, storage, monkeypatch) -> None:
    monkeypatch.setattr(resume_service_module, "dispatch_resume_processing", lambda resume_id: None)
    token = _signup(client, "pending-lifecycle@example.com", "candidate")

    response = _upload(client, token, "r.docx", _docx_bytes("Python backend developer"))
    assert response.status_code == 201
    body = response.json()
    assert body["processing_status"] == "pending"
    assert body["parsed_text"] is None
    resume_id = body["id"]

    pending = client.get(f"/api/v1/resumes/{resume_id}", headers={"Authorization": f"Bearer {token}"})
    assert pending.json()["processing_status"] == "pending"

    process_resume(db_session, uuid.UUID(resume_id), storage=storage)  # "the worker runs"

    done = client.get(f"/api/v1/resumes/{resume_id}", headers={"Authorization": f"Bearer {token}"})
    assert done.json()["processing_status"] == "completed"
    assert "Python" in done.json()["parsed_text"]


@pytest.mark.unit
def test_enqueue_failure_marks_resume_failed(client: TestClient, storage, monkeypatch) -> None:
    def broker_down(resume_id):
        raise RuntimeError("broker unreachable")

    monkeypatch.setattr(resume_service_module, "dispatch_resume_processing", broker_down)
    token = _signup(client, "enqueue-failure@example.com", "candidate")

    response = _upload(client, token, "r.docx", _docx_bytes("Some resume content"))

    assert response.status_code == 201
    assert response.json()["processing_status"] == "failed"


@pytest.mark.unit
def test_corrupt_upload_ends_failed_not_crashed(client: TestClient, storage) -> None:
    token = _signup(client, "corrupt-upload@example.com", "candidate")

    response = _upload(client, token, "bad.docx", b"definitely not a docx")

    assert response.status_code == 201
    assert response.json()["processing_status"] == "failed"
    assert response.json()["parsed_text"] is None


@pytest.mark.unit
def test_apply_requires_processed_resume(client: TestClient, db_session, storage, monkeypatch) -> None:
    recruiter_token = _signup(client, "guard-recruiter@example.com", "recruiter")
    job = client.post(
        "/api/v1/jobs/",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"title": "Backend Engineer", "description": "Build backend services in Python."},
    ).json()
    client.patch(
        f"/api/v1/jobs/{job['id']}/status",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"status": "open"},
    )

    monkeypatch.setattr(resume_service_module, "dispatch_resume_processing", lambda resume_id: None)
    candidate_token = _signup(client, "guard-candidate@example.com", "candidate")
    resume_id = _upload(client, candidate_token, "r.docx", _docx_bytes("Python developer")).json()["id"]

    blocked = client.post(
        "/api/v1/applications/",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"job_id": job["id"], "resume_id": resume_id},
    )
    assert blocked.status_code == 409

    process_resume(db_session, uuid.UUID(resume_id), storage=storage)

    allowed = client.post(
        "/api/v1/applications/",
        headers={"Authorization": f"Bearer {candidate_token}"},
        json={"job_id": job["id"], "resume_id": resume_id},
    )
    assert allowed.status_code == 201


@pytest.mark.unit
def test_insights_require_processed_resume(client: TestClient, storage, monkeypatch) -> None:
    """The guard runs before any LLM call, so this test spends no API quota."""
    monkeypatch.setattr(resume_service_module, "dispatch_resume_processing", lambda resume_id: None)
    token = _signup(client, "insights-guard@example.com", "candidate")
    resume_id = _upload(client, token, "r.docx", _docx_bytes("Some content")).json()["id"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get(f"/api/v1/insights/resumes/{resume_id}/summary", headers=headers).status_code == 409
    assert client.get(f"/api/v1/insights/resumes/{resume_id}/improvements", headers=headers).status_code == 409


# --------------------------- celery wiring ---------------------------


@pytest.mark.unit
def test_dispatch_enqueues_celery_task_with_string_id(monkeypatch) -> None:
    """Task arguments travel as JSON, so the UUID must be passed as a string."""

    class FakeTask:
        def __init__(self):
            self.calls = []

        def delay(self, arg):
            self.calls.append(arg)

    fake = FakeTask()
    monkeypatch.setattr("app.workers.tasks.process_resume_task", fake)

    resume_id = uuid.uuid4()
    resume_service_module.dispatch_resume_processing(resume_id)

    assert fake.calls == [str(resume_id)]


@pytest.mark.unit
def test_celery_app_configured_for_safe_at_least_once_delivery() -> None:
    import app.workers.tasks  # noqa: F401  (registers the task)
    from app.workers.celery_app import celery_app

    assert "resumes.process" in celery_app.tasks
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_prefetch_multiplier == 1
