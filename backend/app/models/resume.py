"""
Resume model — an uploaded resume file and its parsed representation.
"""

import enum
import uuid
from typing import List, Optional

from sqlalchemy import Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin


class FileType(str, enum.Enum):
    """Supported resume upload formats."""

    PDF = "pdf"
    DOCX = "docx"


class EducationLevel(str, enum.Enum):
    """
    Ordered education levels, produced by the Milestone 5 extraction
    pipeline and consumed by the Milestone 7 scoring engine to compare
    a candidate's education against a job's minimum requirement.

    Values are ordered low-to-high so `list(EducationLevel)` can rank
    levels directly without a separate lookup table.
    """

    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    An uploaded resume belonging to a candidate.

    `storage_path` points to where the raw file lives on disk (Milestone 4
    will introduce proper object storage abstraction — local disk for now,
    swappable for S3-compatible storage later without changing this schema).

    `parsed_text` is populated asynchronously by a Celery worker after
    upload (Milestone 4/10) — nullable because a freshly uploaded resume
    hasn't been parsed yet, and the API needs to represent that "pending"
    state honestly rather than pretending it's already done.
    """

    __tablename__ = "resumes"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[FileType] = mapped_column(Enum(FileType, name="file_type"), nullable=False)
    parsed_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Structured extraction results (Milestone 5) ---
    # Nullable throughout: a freshly uploaded or unparseable resume has
    # no extracted data yet, and the API should represent that honestly
    # rather than defaulting to a misleading 0.
    extracted_years_experience: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extracted_education_level: Mapped[Optional[EducationLevel]] = mapped_column(
        Enum(EducationLevel, name="education_level"), nullable=True
    )

    # --- Relationships ---
    candidate: Mapped["User"] = relationship(back_populates="resumes")
    applications: Mapped[List["Application"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    resume_skills: Mapped[List["ResumeSkill"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} filename={self.original_filename}>"
