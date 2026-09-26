"""Application model linking a resume to a job with workflow status."""

import enum
import uuid
from typing import Optional

from sqlalchemy import Enum, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin


class ApplicationStatus(str, enum.Enum):
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    HIRED = "hired"


class Application(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "applications"
    __table_args__ = (
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

    # --- LLM-generated interview questions (Milestone 9) ---
    # Lives on Application, not Resume, because questions are tailored
    # to a specific resume-job pairing -- the same resume applied to a
    # different job would warrant different questions.
    interview_questions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

    job: Mapped["Job"] = relationship(back_populates="applications")
    resume: Mapped["Resume"] = relationship(back_populates="applications")
    score: Mapped[Optional["Score"]] = relationship(
        back_populates="application", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Application id={self.id} job_id={self.job_id} status={self.status}>"
