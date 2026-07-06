"""
Unit tests for ORM models and their relationships.

These run against a real (throwaway) SQLite database rather than
mocking SQLAlchemy — mocking an ORM tends to test the mock, not the
mapping. SQLite is close enough to Postgres for structural checks
(relationships, cascades, constraints) even though we use Postgres in
production; anything SQLite can't emulate (like JSONB) is exercised
separately in the integration tests against real Postgres.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base_class import Base
from app.models import (
    Application,
    ApplicationStatus,
    Job,
    JobStatus,
    Resume,
    FileType,
    Score,
    Skill,
    User,
    UserRole,
)


@pytest.fixture()
def db_session():
    """A fresh in-memory SQLite DB per test, torn down automatically."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.mark.unit
def test_create_user_and_relationships(db_session: Session) -> None:
    """A recruiter can be created and starts with no posted jobs."""
    recruiter = User(
        email="recruiter@example.com",
        hashed_password="hashed",
        full_name="Jane Recruiter",
        role=UserRole.RECRUITER,
    )
    db_session.add(recruiter)
    db_session.commit()

    assert recruiter.id is not None
    assert recruiter.jobs_posted == []


@pytest.mark.unit
def test_job_application_score_chain(db_session: Session) -> None:
    """
    End-to-end relationship chain: recruiter -> job -> application <- resume <- candidate,
    with a 1:1 score attached to the application.
    """
    recruiter = User(
        email="recruiter2@example.com",
        hashed_password="hashed",
        full_name="Rita Recruiter",
        role=UserRole.RECRUITER,
    )
    candidate = User(
        email="candidate@example.com",
        hashed_password="hashed",
        full_name="Cal Candidate",
        role=UserRole.CANDIDATE,
    )
    job = Job(
        recruiter=recruiter,
        title="Backend Engineer",
        description="Build APIs",
        min_experience_years=2,
        status=JobStatus.OPEN,
    )
    resume = Resume(
        candidate=candidate,
        original_filename="resume.pdf",
        storage_path="/uploads/resume.pdf",
        file_type=FileType.PDF,
    )
    application = Application(job=job, resume=resume, status=ApplicationStatus.APPLIED)
    score = Score(
        application=application,
        skills_match_score=80.0,
        overall_score=75.0,
        explanation={"matched_skills": ["python"]},
    )

    db_session.add_all([recruiter, candidate, job, resume, application, score])
    db_session.commit()

    assert application.job.title == "Backend Engineer"
    assert application.resume.candidate.email == "candidate@example.com"
    assert application.score.overall_score == 75.0
    assert application.score.explanation["matched_skills"] == ["python"]


@pytest.mark.unit
def test_duplicate_application_is_rejected(db_session: Session) -> None:
    """
    The unique constraint on (job_id, resume_id) should prevent a resume
    from being submitted twice to the same job.
    """
    from sqlalchemy.exc import IntegrityError

    recruiter = User(
        email="r3@example.com", hashed_password="x", full_name="R", role=UserRole.RECRUITER
    )
    candidate = User(
        email="c3@example.com", hashed_password="x", full_name="C", role=UserRole.CANDIDATE
    )
    job = Job(recruiter=recruiter, title="QA Engineer", description="Test things")
    resume = Resume(
        candidate=candidate,
        original_filename="r.pdf",
        storage_path="/uploads/r.pdf",
        file_type=FileType.PDF,
    )
    db_session.add_all([recruiter, candidate, job, resume])
    db_session.commit()

    db_session.add(Application(job_id=job.id, resume_id=resume.id))
    db_session.commit()

    db_session.add(Application(job_id=job.id, resume_id=resume.id))
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.unit
def test_skill_name_uniqueness(db_session: Session) -> None:
    """Two skills can't share the same canonical name."""
    from sqlalchemy.exc import IntegrityError

    db_session.add(Skill(name="Python", category="Programming Language"))
    db_session.commit()

    db_session.add(Skill(name="Python", category="Programming Language"))
    with pytest.raises(IntegrityError):
        db_session.commit()
