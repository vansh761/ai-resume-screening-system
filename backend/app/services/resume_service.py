"""
Resume upload service.

Design decision
----------------
This is where validation, storage, and text extraction are
orchestrated — but notice each of those concerns lives in its own
module (`app/services/storage/`, `app/ai/text_extraction.py`,
`app/ai/text_cleaning.py`) and this file only sequences them. That
separation is what lets each piece be unit-tested independently (does
storage work? does extraction work? does cleaning work?) as well as
together (does the whole upload flow work?).

Parsing failures are handled gracefully, not fatally: if text
extraction fails (e.g. a corrupted or scanned-image-only PDF), the
resume record is still created with `parsed_text = None` rather than
rejecting the upload outright. A candidate whose PDF happens to be
awkward shouldn't be told "upload failed" when the file itself was
saved successfully — later milestones (the recruiter dashboard) can
surface "parsing incomplete" as its own state.
"""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.education_extraction import extract_education_level
from app.ai.experience_extraction import extract_years_experience
from app.ai.skill_extraction import extract_skills_for_resume
from app.ai.text_cleaning import clean_text
from app.ai.text_extraction import TextExtractionError, extract_text
from app.core.config import settings
from app.core.logging_config import get_logger
from app.models.resume import FileType, Resume
from app.models.skill import ResumeSkill
from app.models.user import User
from app.services.storage import get_storage_backend

logger = get_logger(__name__)

ALLOWED_EXTENSION_TO_FILETYPE = {
    ".pdf": FileType.PDF,
    ".docx": FileType.DOCX,
}


class UnsupportedFileTypeError(Exception):
    """Raised when an uploaded file's extension isn't in the allow-list."""


class FileTooLargeError(Exception):
    """Raised when an uploaded file exceeds the configured size limit."""


def _validate_and_resolve_file_type(filename: str, file_bytes: bytes) -> FileType:
    """
    Validates extension against the configured allow-list and file size
    against the configured limit, returning the resolved `FileType`.

    Validating the extension against an explicit allow-list (rather
    than a deny-list of "bad" extensions) is a security best practice:
    an allow-list fails safe — anything not explicitly permitted is
    rejected — whereas a deny-list only blocks what you already thought
    to list.
    """
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


def upload_resume(db: Session, candidate: User, filename: str, file_bytes: bytes) -> Resume:
    """
    Validates, stores, and parses a resume upload for the given candidate.

    Returns the created `Resume` row. `parsed_text` will be populated
    unless extraction failed, in which case it's left `None` and the
    failure is logged — see the module docstring for why this doesn't
    fail the whole request.
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
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    try:
        raw_text = extract_text(file_bytes, file_type)
        resume.parsed_text = clean_text(raw_text)
        db.commit()
        db.refresh(resume)

        # Structured extraction (Milestone 5): runs only if text
        # extraction succeeded -- there's nothing to extract skills or
        # experience from if we couldn't get plain text in the first
        # place. Each sub-extractor is independent and best-effort;
        # a failure in one (e.g., no education keywords found) doesn't
        # block the others from running.
        matched_skills = extract_skills_for_resume(db, resume.parsed_text)
        for skill in matched_skills:
            db.add(ResumeSkill(resume_id=resume.id, skill_id=skill.id))

        resume.extracted_years_experience = extract_years_experience(resume.parsed_text)
        resume.extracted_education_level = extract_education_level(resume.parsed_text)
        db.commit()
        db.refresh(resume)
    except TextExtractionError as exc:
        # Deliberately swallowed: the resume record and file are already
        # saved successfully. A parsing failure is a degraded state, not
        # a fatal one -- logged here so it's visible in ops/monitoring,
        # and worth building an admin-facing "reprocess" action for in a
        # later milestone rather than failing the upload outright.
        logger.warning(f"Text extraction failed for resume {resume.id}: {exc}")

    return resume


def get_resume_for_candidate(db: Session, resume_id: uuid.UUID, candidate_id: uuid.UUID) -> Resume | None:
    """
    Fetches a resume, scoped to its owning candidate.

    Returns None both when the resume doesn't exist AND when it exists
    but belongs to someone else -- the caller should turn either case
    into an identical 404. Distinguishing "doesn't exist" from "exists
    but isn't yours" in the response would leak which resume IDs are
    valid to an attacker probing IDs, the same enumeration concern as
    the login error message in Milestone 3.
    """
    return db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.candidate_id == candidate_id)
    ).scalar_one_or_none()


def list_resumes_for_candidate(db: Session, candidate_id: uuid.UUID) -> Sequence[Resume]:
    """Returns all resumes belonging to a given candidate."""
    return db.execute(
        select(Resume).where(Resume.candidate_id == candidate_id).order_by(Resume.created_at.desc())
    ).scalars().all()
