"""Application endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.application import ApplicationCreate, ApplicationRead
from app.services.application_service import (
    DuplicateApplicationError,
    ResumeNotOwnedError,
    create_application,
    list_applications_for_candidate,
    list_applications_for_job,
)
from app.services.job_service import get_job
from app.services.resume_service import get_resume_for_candidate

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("/", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def apply_to_job(
    application_in: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
) -> ApplicationRead:
    job = get_job(db, application_in.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    resume = get_resume_for_candidate(db, application_in.resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    try:
        application = create_application(db, current_user.id, job, resume)
    except DuplicateApplicationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ResumeNotOwnedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))

    return application


@router.get("/mine", response_model=list[ApplicationRead])
def list_my_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
) -> list[ApplicationRead]:
    return list_applications_for_candidate(db, current_user.id)


@router.get("/for-job/{job_id}", response_model=list[ApplicationRead])
def list_applications_for_job_endpoint(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> list[ApplicationRead]:
    job = get_job(db, job_id)
    if job is None or job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return list_applications_for_job(db, job_id)
