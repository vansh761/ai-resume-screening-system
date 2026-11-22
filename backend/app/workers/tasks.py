"""
Celery tasks.

Each task is a thin wrapper: open a DB session, call a service
function, close the session. All real logic lives in the service layer
so it can be tested without Celery.

Retry policy: only transient database errors (OperationalError) are
retried, with exponential backoff and jitter (jitter stops many failed
tasks from all retrying at the same instant). process_resume handles
permanent failures itself by marking the resume FAILED, because
retrying an unreadable file would fail identically every time.
"""

import uuid

from sqlalchemy.exc import OperationalError

from app.db.session import SessionLocal
from app.services.resume_processing_service import process_resume
from app.workers.celery_app import celery_app


@celery_app.task(
    name="resumes.process",
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def process_resume_task(resume_id: str) -> None:
    """Runs the resume processing pipeline for one resume (IDs travel as strings: JSON-only serialization)."""
    db = SessionLocal()
    try:
        process_resume(db, uuid.UUID(resume_id))
    finally:
        db.close()
