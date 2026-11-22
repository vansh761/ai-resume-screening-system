"""
Shared test fixtures.

Background processing in tests
------------------------------
In production, uploading a resume only stores the file and enqueues a
Celery task; a worker process does the NLP/embedding work later. Tests
have no worker, and the real task opens its own database session
(Postgres), not the in-memory SQLite session these tests use.

So the `client` fixture replaces `dispatch_resume_processing` with a
function that runs the same pipeline (`process_resume`) inline, against
the test's own session, before the upload request returns. The
pipeline code under test is identical to production; only WHEN it runs
differs.
"""

from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.services.resume_service as resume_service_module
from app.db.base_class import Base
from app.db.session import get_db
from app.main import create_application
from app.services.resume_processing_service import process_resume


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session: Session, monkeypatch) -> Generator[TestClient, None, None]:
    app = create_application()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    def run_inline(resume_id) -> None:
        # Looked up at call time so per-file `isolate_storage` fixtures
        # (which patch get_storage_backend) are respected.
        process_resume(db_session, resume_id, storage=resume_service_module.get_storage_backend())

    monkeypatch.setattr(resume_service_module, "dispatch_resume_processing", run_inline)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
