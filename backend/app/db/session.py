"""
Database engine and session factory.

Design decision
----------------
We use SQLAlchemy's connection pooling (`pool_size` / `max_overflow`)
rather than opening a fresh connection per request. Connection setup is
expensive (TCP handshake + Postgres auth); a pool reuses warm connections
across requests, which matters once you have concurrent traffic.

`get_db()` is a generator-based FastAPI dependency: it yields a session,
the request handler uses it, and control returns here for cleanup after
the response is sent. This guarantees the session (and its underlying
connection) is always returned to the pool, even if the request handler
raises an exception — the `finally` block always runs.
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    str(settings.DATABASE_URL),
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validates connections before use; avoids "stale connection" errors after DB restarts.
    echo=settings.DEBUG,  # Logs all SQL statements in debug mode — invaluable while learning/debugging queries.
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a request-scoped DB session.

    Usage in an endpoint:
        @router.get("/jobs")
        def list_jobs(db: Session = Depends(get_db)):
            return db.query(Job).all()

    Why a generator instead of just returning a session: FastAPI's
    dependency injection treats functions with `yield` specially — code
    after the `yield` runs as teardown, guaranteed, after the response
    is returned to the client. This is the standard pattern for any
    resource (DB session, file handle) that must be cleaned up per-request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
