"""
Central import point for all ORM models.

Why this file matters
----------------------
Two things depend on every model being imported somewhere before the app
runs:

1. Alembic's `--autogenerate` compares `Base.metadata` (what SQLAlchemy
   knows about) against the live database schema. If a model module is
   never imported, its table never registers itself on `Base.metadata`,
   and Alembic will silently omit it from the migration -- a classic
   "why isn't my new table showing up in the migration" bug.

2. Relationships declared with string references (e.g.
   `Mapped["Job"]` instead of a direct class import, which we use
   throughout to avoid circular imports between model files) are only
   resolved by SQLAlchemy once all the referenced classes have actually
   been imported into memory.

`app/db/session.py` and `alembic/env.py` both import from this module
rather than importing individual model files directly.
"""

from app.models.application import Application, ApplicationStatus
from app.models.job import Job, JobStatus
from app.models.resume import EducationLevel, FileType, Resume
from app.models.score import Score
from app.models.skill import JobSkill, ResumeSkill, Skill
from app.models.user import User, UserRole

__all__ = [
    "User",
    "UserRole",
    "Job",
    "JobStatus",
    "Resume",
    "FileType",
    "EducationLevel",
    "Application",
    "ApplicationStatus",
    "Score",
    "Skill",
    "ResumeSkill",
    "JobSkill",
]
