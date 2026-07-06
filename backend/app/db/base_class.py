"""
Shared SQLAlchemy declarative base and mixins.

Design decision
----------------
Every model in this system needs an `id`, `created_at`, and (for mutable
entities) `updated_at`. Rather than repeating these three columns in every
model file, we define a `Base` class with a `TimestampMixin` that all
models inherit from. This is DRY applied to schema definition — one
change to "how we track record age" (e.g. switching to timezone-aware
timestamps) touches one file, not fifteen.

We also configure a naming convention for constraints (indexes, foreign
keys, unique constraints). Without this, Alembic autogenerates constraint
names like `fk_a1b2c3d4` — unreadable in migration files and impossible
to reference in a manual `DROP CONSTRAINT`. A naming convention makes
every constraint name predictable and greppable.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import CHAR, DateTime, MetaData, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Predictable constraint naming — critical for readable Alembic migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class GUID(TypeDecorator):
    """
    Portable UUID column type: native `UUID` on Postgres, stored as a
    32-char hex string on any other backend (e.g. SQLite).

    Why this exists
    ----------------
    Production runs on Postgres, which has a real native UUID type —
    we want that in production for storage efficiency and correct
    indexing. But our unit test suite (see `tests/unit/test_models.py`)
    intentionally runs against in-memory SQLite for speed, and SQLite
    has no concept of a UUID type at all. Without this adapter, every
    model with a UUID primary/foreign key would only be testable
    against a real, slower, network-dependent Postgres instance —
    defeating the purpose of having a fast unit test tier at all.

    This is the standard SQLAlchemy recipe for cross-dialect UUID
    columns (documented in SQLAlchemy's own docs) rather than a custom
    workaround — worth knowing as the "correct" answer to this problem
    if it comes up in an interview.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return str(value)
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return value


class Base(DeclarativeBase):
    """Base class every ORM model inherits from."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """
    Adds a UUID primary key to any model.

    Generated client-side (Python `uuid.uuid4`) rather than server-side
    (Postgres `gen_random_uuid()`) so the ID is known immediately after
    object construction — useful when a Celery task needs to reference
    a record's ID before the INSERT has committed.
    """

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    """Adds created_at / updated_at columns, both timezone-aware."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
