"""
Resume upload service.
"""

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.education_extraction import extract_education_level
from app.ai.embeddings import embed_text
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


def upload_resume(db: Session, candidate: User, filename: str, file_bytes: bytes) -> Resume:
    """
    Validates, stores, and parses a resume upload for the given candidate.
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

        # Structured extraction (Milestone 5)
        matched_skills = extract_skills_for_resume(db, resume.parsed_text)
        for skill in matched_skills:
            db.add(ResumeSkill(resume_id=resume.id, skill_id=skill.id))

        resume.extracted_years_experience = extract_years_experience(resume.parsed_text)
        resume.extracted_education_level = extract_education_level(resume.parsed_text)

        # Semantic embedding (Milestone 6): computed once at upload
        # time and persisted, so semantic search never needs to re-run
        # the model at query time for existing resumes -- see
        # app/ai/faiss_index.py's docstring for the full reasoning.
        try:
            resume.embedding = embed_text(resume.parsed_text)
        except Exception as embed_exc:
            # Embedding failure shouldn't block the upload any more than
            # a parsing failure should -- the resume and its skills/
            # experience/education are still valid and useful without
            # a semantic vector. It just won't show up in similarity
            # search results until re-processed.
            logger.warning(f"Embedding generation failed for resume {resume.id}: {embed_exc}")

        db.commit()
        db.refresh(resume)
    except TextExtractionError as exc:
        logger.warning(f"Text extraction failed for resume {resume.id}: {exc}")

    return resume


def get_resume_for_candidate(db: Session, resume_id: uuid.UUID, candidate_id: uuid.UUID) -> Resume | None:
    return db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.candidate_id == candidate_id)
    ).scalar_one_or_none()


def list_resumes_for_candidate(db: Session, candidate_id: uuid.UUID) -> Sequence[Resume]:
    return db.execute(
        select(Resume).where(Resume.candidate_id == candidate_id).order_by(Resume.created_at.desc())
    ).scalars().all()
