"""
Re-enqueue resumes stuck in PENDING (the process died between commit and
enqueue, or a worker was lost mid-task). Safe to run repeatedly:
process_resume is idempotent and skips COMPLETED resumes.

Run:  docker compose exec -T backend python scripts/requeue_stale_pending.py [minutes]
"""

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.resume import ProcessingStatus, Resume
from app.services.resume_service import dispatch_resume_processing

minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 15
cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)

db = SessionLocal()
try:
    stale = db.execute(
        select(Resume).where(
            Resume.processing_status == ProcessingStatus.PENDING,
            Resume.updated_at < cutoff,
        )
    ).scalars().all()
    for resume in stale:
        dispatch_resume_processing(resume.id)
        print(f"re-enqueued {resume.id} ({resume.original_filename}), pending since {resume.created_at}")
    print(f"{len(stale)} stale resume(s) re-enqueued")
finally:
    db.close()
