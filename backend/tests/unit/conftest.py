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

from app.db.base_class import Base
from app.db.session import get_db
from app.main import create_application


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
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
