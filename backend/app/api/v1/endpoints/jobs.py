"""Job posting endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.job import Job, JobStatus
from app.models.user import User, UserRole
from app.schemas.job import JobCreate, JobRead, JobStatusUpdate
from app.services.job_service import (
    create_job,
    get_job,
    list_jobs_for_recruiter,
    list_open_jobs,
    update_job_status,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _to_job_read(job: Job) -> JobRead:
    return JobRead(
        id=job.id,
        title=job.title,
        description=job.description,
        department=job.department,
        location=job.location,
        min_experience_years=job.min_experience_years,
        min_education_level=job.min_education_level,
        status=job.status,
        created_at=job.created_at,
        required_skills=sorted(js.skill.name for js in job.job_skills if js.is_required),
        preferred_skills=sorted(js.skill.name for js in job.job_skills if not js.is_required),
    )


@router.post("/", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job_endpoint(
    job_in: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> JobRead:
    job = create_job(
        db,
        recruiter=current_user,
        title=job_in.title,
        description=job_in.description,
        min_experience_years=job_in.min_experience_years,
        min_education_level=job_in.min_education_level,
        department=job_in.department,
        location=job_in.location,
        required_skill_names=job_in.required_skills,
        preferred_skill_names=job_in.preferred_skills,
    )
    return _to_job_read(job)


@router.get("/", response_model=list[JobRead])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[JobRead]:
    if current_user.role == UserRole.RECRUITER:
        jobs = list_jobs_for_recruiter(db, current_user.id)
    else:
        jobs = list_open_jobs(db)
    return [_to_job_read(j) for j in jobs]


@router.get("/{job_id}", response_model=JobRead)
def get_job_endpoint(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobRead:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if current_user.role == UserRole.CANDIDATE and job.status != JobStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if current_user.role == UserRole.RECRUITER and job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _to_job_read(job)


@router.patch("/{job_id}/status", response_model=JobRead)
def update_job_status_endpoint(
    job_id: uuid.UUID,
    status_update: JobStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> JobRead:
    job = get_job(db, job_id)
    if job is None or job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job = update_job_status(db, job, status_update.status)
    return _to_job_read(job)
