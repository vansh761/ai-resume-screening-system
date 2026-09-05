"""
Application service.
"""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.scoring import compute_score
from app.models.application import Application, ApplicationStatus
from app.models.job import Job
from app.models.resume import Resume
from app.models.score import Score


class DuplicateApplicationError(Exception):
    pass


class ResumeNotOwnedError(Exception):
    pass


def create_application(db: Session, candidate_id: uuid.UUID, job: Job, resume: Resume) -> Application:
    if resume.candidate_id != candidate_id:
        raise ResumeNotOwnedError("You can only apply using your own resume.")

    existing = db.execute(
        select(Application).where(Application.job_id == job.id, Application.resume_id == resume.id)
    ).scalar_one_or_none()
    if existing is not None:
        raise DuplicateApplicationError("You have already applied to this job with this resume.")

    application = Application(job_id=job.id, resume_id=resume.id, status=ApplicationStatus.APPLIED)
    db.add(application)
    db.commit()
    db.refresh(application)

    breakdown = compute_score(resume, job)
    score = Score(
        application_id=application.id,
        skills_match_score=breakdown.skills_match_score,
        experience_match_score=breakdown.experience_match_score,
        education_match_score=breakdown.education_match_score,
        certification_score=breakdown.certification_score,
        project_score=breakdown.project_score,
        ats_score=breakdown.ats_score,
        resume_quality_score=breakdown.resume_quality_score,
        semantic_similarity_score=breakdown.semantic_similarity_score,
        overall_score=breakdown.overall_score,
        explanation=breakdown.explanation,
    )
    db.add(score)
    db.commit()
    db.refresh(application)

    return application


def get_application(db: Session, application_id: uuid.UUID) -> Application | None:
    return db.get(Application, application_id)


def list_applications_for_job(db: Session, job_id: uuid.UUID) -> Sequence[Application]:
    return db.execute(
        select(Application)
        .join(Score, Score.application_id == Application.id)
        .where(Application.job_id == job_id)
        .order_by(Score.overall_score.desc())
    ).scalars().all()


def list_applications_for_candidate(db: Session, candidate_id: uuid.UUID) -> Sequence[Application]:
    return db.execute(
        select(Application)
        .join(Resume, Resume.id == Application.resume_id)
        .where(Resume.candidate_id == candidate_id)
        .order_by(Application.created_at.desc())
    ).scalars().all()
