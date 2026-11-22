"""
Resume upload service.

Since Milestone 10, uploading is fast and asynchronous: validate, store
the file, create the Resume row as PENDING, commit, then enqueue
background processing (app/services/resume_processing_service.py,
executed by a Celery worker).

Commit BEFORE enqueue: the worker must be able to see the row.
Known gap: if this process dies between the commit and the enqueue,
the resume stays PENDING forever. Production fixes are a periodic
sweeper (Celery Beat) that re-enqueues stale PENDING resumes, or a
transactional outbox. Not built here; documented on purpose.
"""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.resume import FileType, ProcessingStatus, Resume
from app.models.user import User
from app.services.storage import get_storage_backend

logger = get_logger(__name__)

ALLOWED_EXTENSION_TO_FILETYPE = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
}


class UnsupportedFileTypeError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


def _validate_and_resolve_file_type(filename: str, file_bytes: bytes) -> FileType:
    suffix = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix not in ALLOWED_EXTENSION_TO_FILETYPE:
        raise UnsupportedFileTypeError(
            f"Unsupported file extension '{suffix}'. "
            f"Allowed: {', '.join(settings.ALLOWED_RESUME_EXTENSIONS)}"
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise FileTooLargeError(
            f"File exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB"
        )

    return ALLOWED_EXTENSION_TO_FILETYPE[suffix]


def dispatch_resume_processing(resume_id: uuid.UUID) -> None:
    """
    Enqueues background processing for a resume.

    This is a deliberate seam: it is a module-level function so tests
    can replace it with an inline runner (see tests/unit/conftest.py).
    The Celery import is lazy so merely importing this module never
    touches the broker.
    """
    from app.workers.tasks import process_resume_task

    process_resume_task.delay(str(resume_id))


def upload_resume(db: Session, candidate: User, filename: str, file_bytes: bytes) -> Resume:
    """
    Validates and stores an upload, then enqueues processing.

    Returns the Resume immediately, typically still PENDING. If the
    broker is unreachable the resume is marked FAILED (visible to the
    user) rather than left PENDING forever.
    """
    file_type = _validate_and_resolve_file_type(filename, file_bytes)

    storage_key = f"{candidate.id}/{uuid.uuid4().hex}_{filename}"
    storage = get_storage_backend()
    storage.save(file_bytes, storage_key)

    resume = Resume(
        candidate_id=candidate.id,
        original_filename=filename,
        storage_path=storage_key,
        file_type=file_type,
        parsed_text=None,
        processing_status=ProcessingStatus.PENDING,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    try:
        dispatch_resume_processing(resume.id)
    except Exception:
        logger.exception(f"Failed to enqueue processing for resume {resume.id}")
        db.rollback()
        resume.processing_status = ProcessingStatus.FAILED
        db.commit()

    return resume


def get_resume_for_candidate(db: Session, resume_id: uuid.UUID, candidate_id: uuid.UUID) -> Resume | None:
    return db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.candidate_id == candidate_id)
    ).scalar_one_or_none()


def list_resumes_for_candidate(db: Session, candidate_id: uuid.UUID) -> Sequence[Resume]:
    return db.execute(
        select(Resume).where(Resume.candidate_id == candidate_id).order_by(Resume.created_at.desc())
    ).scalars().all()
