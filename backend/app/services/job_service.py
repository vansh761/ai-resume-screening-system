"""
Job posting service.
"""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import embed_text
from app.core.logging_config import get_logger
from app.models.job import Job, JobStatus
from app.models.skill import JobSkill, Skill
from app.models.user import User

logger = get_logger(__name__)


def create_job(
    db: Session,
    recruiter: User,
    title: str,
    description: str,
    min_experience_years: int,
    min_education_level: str | None,
    department: str | None,
    location: str | None,
    required_skill_names: list[str],
    preferred_skill_names: list[str],
) -> Job:
    job = Job(
        recruiter_id=recruiter.id,
        title=title,
        description=description,
        department=department,
        location=location,
        min_experience_years=min_experience_years,
        min_education_level=min_education_level,
        status=JobStatus.DRAFT,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    _attach_skills(db, job, required_skill_names, is_required=True)
    _attach_skills(db, job, preferred_skill_names, is_required=False)

    try:
        job.embedding = embed_text(f"{title}\n{description}")
    except Exception as exc:
        logger.warning(f"Embedding generation failed for job {job.id}: {exc}")

    db.commit()
    db.refresh(job)
    return job


def _attach_skills(db: Session, job: Job, skill_names: list[str], is_required: bool) -> None:
    if not skill_names:
        return
    known_skills = db.execute(select(Skill).where(Skill.name.in_(skill_names))).scalars().all()
    for skill in known_skills:
        db.add(JobSkill(job_id=job.id, skill_id=skill.id, is_required=is_required))
    db.commit()


def get_job(db: Session, job_id: uuid.UUID) -> Job | None:
    return db.get(Job, job_id)


def list_jobs_for_recruiter(db: Session, recruiter_id: uuid.UUID) -> Sequence[Job]:
    return db.execute(
        select(Job).where(Job.recruiter_id == recruiter_id).order_by(Job.created_at.desc())
    ).scalars().all()


def list_open_jobs(db: Session) -> Sequence[Job]:
    return db.execute(
        select(Job).where(Job.status == JobStatus.OPEN).order_by(Job.created_at.desc())
    ).scalars().all()


def update_job_status(db: Session, job: Job, new_status: JobStatus) -> Job:
    job.status = new_status
    db.commit()
    db.refresh(job)
    return job
