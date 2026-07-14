"""
Shared test fixtures.

Design decision
----------------
We override FastAPI's `get_db` dependency to point at a fresh in-memory
SQLite database, created and torn down per test. This is the standard
FastAPI testing pattern: `app.dependency_overrides` swaps out a
dependency for the entire app without touching any endpoint code —
the endpoints have no idea they're talking to SQLite instead of the
real Postgres. Each test gets a completely clean database, so tests
can never leak state into one another regardless of execution order.
"""

from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base
from app.db.session import get_db
from app.main import create_application


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    # `StaticPool` forces every checkout to reuse the SAME underlying
    # connection, regardless of which thread requests it.
    #
    # Why this matters: FastAPI's TestClient dispatches each request to
    # a worker thread (see `anyio.to_thread.run_sync` in any traceback
    # from an endpoint under test). SQLAlchemy's default SQLite pooling
    # hands out a connection per thread — so without StaticPool, the
    # connection that ran `Base.metadata.create_all()` here (in the
    # test's main thread) is a completely separate, empty in-memory
    # database from the one the endpoint's worker thread queries
    # against. Same `sqlite:///:memory:` URL, different actual database
    # — which is exactly what produced "no such table: users" even
    # though the table genuinely was created, just on a connection the
    # request never saw.
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
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_application()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
