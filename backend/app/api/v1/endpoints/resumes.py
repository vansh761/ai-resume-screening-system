"""
Resume endpoints: upload, fetch, and list — all scoped to the
authenticated candidate. Recruiter access to candidate resumes (for
reviewing applications) comes in a later milestone once applications
exist end-to-end; deliberately out of scope here to keep this
milestone's surface area focused on upload + parsing.
"""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.resume import ResumeRead, ResumeSummary
from app.services.resume_service import (
    FileTooLargeError,
    UnsupportedFileTypeError,
    get_resume_for_candidate,
    list_resumes_for_candidate,
    upload_resume,
)

router = APIRouter(prefix="/resumes", tags=["Resumes"])


def _to_resume_read(resume: Resume) -> ResumeRead:
    """
    Builds a `ResumeRead` from a `Resume` ORM object.

    Not a plain `ResumeRead.model_validate(resume)` because
    `extracted_skills` is derived from the `resume_skills` relationship
    (a list of `ResumeSkill` join rows, each pointing to a `Skill`),
    not a direct column on `Resume` -- `from_attributes` conversion has
    no way to know how to flatten that relationship into a list of
    names on its own.
    """
    return ResumeRead(
        id=resume.id,
        original_filename=resume.original_filename,
        file_type=resume.file_type,
        parsed_text=resume.parsed_text,
        created_at=resume.created_at,
        extracted_skills=sorted(rs.skill.name for rs in resume.resume_skills),
        years_experience=resume.extracted_years_experience,
        education_level=resume.extracted_education_level,
    )


@router.post("/upload", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def upload_resume_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
) -> ResumeRead:
    """
    Uploads a resume (PDF or DOCX) for the authenticated candidate.

    Reads the entire file into memory before validation — acceptable
    for the size limits configured here (default 10 MB); a truly
    large-file-tolerant version would stream and check size
    incrementally, a documented future improvement once real usage
    patterns justify the added complexity.
    """
    file_bytes = await file.read()

    try:
        resume = upload_resume(db, current_user, file.filename, file_bytes)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except FileTooLargeError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc))

    return _to_resume_read(resume)


@router.get("/", response_model=list[ResumeSummary])
def list_my_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
) -> list[ResumeSummary]:
    """Lists all resumes uploaded by the authenticated candidate."""
    resumes = list_resumes_for_candidate(db, current_user.id)
    return [
        ResumeSummary(
            id=r.id,
            original_filename=r.original_filename,
            file_type=r.file_type,
            created_at=r.created_at,
            has_parsed_text=r.parsed_text is not None,
        )
        for r in resumes
    ]


@router.get("/{resume_id}", response_model=ResumeRead)
def get_my_resume(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
) -> ResumeRead:
    """
    Fetches a single resume, including its full parsed text.

    Returns 404 (not 403) when the resume belongs to someone else --
    see `get_resume_for_candidate`'s docstring for why that
    distinction matters.
    """
    resume = get_resume_for_candidate(db, resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return _to_resume_read(resume)
