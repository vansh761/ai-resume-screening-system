"""Integration test: verifies our models work against a REAL Postgres instance."""

import uuid
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base_class import Base
from app.models import Job, JobStatus, Score, User, UserRole


@pytest.fixture(scope="module")
def pg_engine():
    engine = create_engine(str(settings.DATABASE_URL))
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Postgres not reachable, skipping integration test: {exc}")

    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.mark.integration
def test_jsonb_explanation_round_trips_through_postgres(pg_engine) -> None:
    with Session(pg_engine) as session:
        recruiter = User(email=f"pg-recruiter-{uuid.uuid4().hex[:8]}@example.com", hashed_password="x",
                          full_name="PG Recruiter", role=UserRole.RECRUITER)
        job = Job(recruiter=recruiter, title="Data Engineer", description="ETL pipelines")
        session.add_all([recruiter, job])
        session.commit()

        from app.models import Application, Resume, FileType

        candidate = User(email=f"pg-candidate-{uuid.uuid4().hex[:8]}@example.com", hashed_password="x",
                          full_name="PG Candidate", role=UserRole.CANDIDATE)
        resume = Resume(candidate=candidate, original_filename="pg_test.pdf",
                         storage_path="/uploads/pg_test.pdf", file_type=FileType.PDF)
        application = Application(job=job, resume=resume)
        explanation_payload = {
            "matched_skills": ["python", "airflow"],
            "missing_skills": ["dbt"],
            "weights_used": {"skills": 0.3, "experience": 0.2},
        }
        score = Score(application=application, overall_score=82.5, explanation=explanation_payload)
        session.add_all([candidate, resume, application, score])
        session.commit()

        fetched = session.get(Score, score.id)
        assert fetched is not None
        assert fetched.explanation == explanation_payload
        assert fetched.explanation["matched_skills"] == ["python", "airflow"]
