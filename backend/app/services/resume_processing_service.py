"""
Resume processing pipeline: text extraction -> cleaning -> structured
extraction (skills/experience/education) -> embedding.

In production this runs inside a Celery worker (app/workers/tasks.py).
It lives in the service layer and takes a plain SQLAlchemy Session so
the exact same logic can be called from a worker, a test, or a script,
with no Celery machinery involved.

Idempotency
-----------
Celery is configured for at-least-once delivery (task_acks_late), so
this function can run more than once for the same resume (e.g. a
worker dies mid-task and the message is redelivered). It therefore:
  - returns immediately if the resume is already COMPLETED, and
  - clears any previously-saved ResumeSkill rows before re-adding them,
    so a retry can't violate the (resume_id, skill_id) unique constraint.

Failure handling
----------------
  - Permanent failures (unreadable/missing file) -> status FAILED. A
    retry would fail identically, so we don't raise.
  - Transient database errors (OperationalError) are re-raised so the
    Celery task wrapper can retry with backoff.
  - Embedding failure is non-fatal (same policy as before this
    milestone): the resume completes without a vector and is simply
    absent from semantic search until reprocessed.
"""

import uuid

from sqlalchemy import delete
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.ai.education_extraction import extract_education_level
from app.ai.embeddings import embed_text
from app.ai.experience_extraction import extract_years_experience
from app.ai.skill_extraction import extract_skills_for_resume
from app.ai.text_cleaning import clean_text
from app.ai.text_extraction import TextExtractionError, extract_text
from app.core.logging_config import get_logger
from app.models.resume import ProcessingStatus, Resume
from app.models.skill import ResumeSkill
from app.services.storage import StorageBackend, get_storage_backend

logger = get_logger(__name__)


def _mark_failed(db: Session, resume_id: uuid.UUID, reason: str) -> None:
    db.rollback()
    resume = db.get(Resume, resume_id)
    if resume is not None:
        resume.processing_status = ProcessingStatus.FAILED
        db.commit()
    logger.warning(f"Resume {resume_id} processing failed: {reason}")


def process_resume(
    db: Session, resume_id: uuid.UUID, storage: StorageBackend | None = None
) -> None:
    """
    Runs the full processing pipeline for one resume and records the
    outcome in `Resume.processing_status`.

    `storage` is injectable so tests can supply the backend they
    installed; production callers omit it and get the configured one.
    """
    resume = db.get(Resume, resume_id)
    if resume is None:
        logger.warning(f"process_resume: resume {resume_id} not found; skipping")
        return
    if resume.processing_status == ProcessingStatus.COMPLETED:
        logger.info(f"process_resume: resume {resume_id} already completed; skipping")
        return

    storage = storage or get_storage_backend()

    try:
        file_bytes = storage.read(resume.storage_path)
        raw_text = extract_text(file_bytes, resume.file_type)
        resume.parsed_text = clean_text(raw_text)
        db.commit()

        matched_skills = extract_skills_for_resume(db, resume.parsed_text)
        db.execute(delete(ResumeSkill).where(ResumeSkill.resume_id == resume.id))
        for skill in matched_skills:
            db.add(ResumeSkill(resume_id=resume.id, skill_id=skill.id))

        resume.extracted_years_experience = extract_years_experience(resume.parsed_text)
        resume.extracted_education_level = extract_education_level(resume.parsed_text)

        try:
            resume.embedding = embed_text(resume.parsed_text)
        except Exception as embed_exc:
            logger.warning(f"Embedding generation failed for resume {resume_id}: {embed_exc}")

        resume.processing_status = ProcessingStatus.COMPLETED
        db.commit()
    except OperationalError:
        db.rollback()
        raise
    except (TextExtractionError, FileNotFoundError) as exc:
        _mark_failed(db, resume_id, str(exc))
    except Exception:
        logger.exception(f"Unexpected error processing resume {resume_id}")
        _mark_failed(db, resume_id, "unexpected error")
