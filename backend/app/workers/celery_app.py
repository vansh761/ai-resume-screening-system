"""
Celery application.

Configuration choices worth being able to explain:

- Redis as broker: already running since Milestone 1, and plenty for
  this scale. (RabbitMQ offers stronger delivery guarantees and routing
  at the cost of another service to operate.)
- JSON-only serialization: Celery can pickle task payloads, but
  unpickling untrusted data is arbitrary code execution. Anyone who can
  write to the broker could then run code in the worker. JSON removes
  that whole class of risk.
- task_acks_late + task_reject_on_worker_lost: a task is acknowledged
  only AFTER it finishes, so if a worker dies mid-task the message is
  redelivered instead of silently lost. The price is at-least-once
  delivery: a task may run twice, so tasks must be idempotent (see
  resume_processing_service.process_resume).
- worker_prefetch_multiplier=1: by default a worker reserves several
  messages ahead of time. For long tasks (model inference) that lets one
  busy worker hoard messages while others sit idle.
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "resume_screening",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)
