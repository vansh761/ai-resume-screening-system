"""
Application model — the fact that a candidate's resume was submitted
for a specific job. See Milestone 2 discussion for why this exists as
its own entity rather than a plain many-to-many table.
"""

import enum
import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin


class ApplicationStatus(str, enum.Enum):
    """Workflow state of a single application, tracked independently of scoring."""

    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    HIRED = "hired"


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A candidate's resume submitted against a specific job posting."""

    __tablename__ = "applications"
    __table_args__ = (
        # A candidate shouldn't be able to apply to the same job twice
        # with the same resume — this constraint enforces that at the
        # database level, not just in application code (which can be
        # bypassed by a race condition or a direct DB write).
        UniqueConstraint("job_id", "resume_id", name="uq_application_job_resume"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"),
        default=ApplicationStatus.APPLIED,
        nullable=False,
    )

    # --- Relationships ---
    job: Mapped["Job"] = relationship(back_populates="applications")
    resume: Mapped["Resume"] = relationship(back_populates="applications")
    score: Mapped[Optional["Score"]] = relationship(
        back_populates="application", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} job_id={self.job_id} status={self.status}>"
