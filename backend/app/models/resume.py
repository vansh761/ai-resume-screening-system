"""
Resume model - an uploaded resume file and its parsed representation.
"""

import enum
import uuid
from typing import List, Optional

from sqlalchemy import Enum, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin


class FileType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"


class EducationLevel(str, enum.Enum):
    """
    Ordered education levels, produced by the Milestone 5 extraction
    pipeline and consumed by the Milestone 7 scoring engine.
    """

    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTORATE = "doctorate"


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    An uploaded resume belonging to a candidate.
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
    extracted_years_experience: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    extracted_education_level: Mapped[Optional[EducationLevel]] = mapped_column(
        Enum(EducationLevel, name="education_level"), nullable=True
    )

    # --- Semantic embedding (Milestone 6) ---
    # Stored as a plain JSON array of floats rather than pgvector, to
    # avoid requiring the pgvector Postgres extension for a portfolio
    # project -- FAISS (in-memory, assembled per search) handles the
    # actual similarity search, so Postgres only needs to durably store
    # the raw vector, not query over it directly. A JSON column (not
    # JSONB-only) keeps this portable to SQLite for fast unit tests,
    # same reasoning as Score.explanation in Milestone 2.
    embedding: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)

    # --- LLM-generated insights (Milestone 9) ---
    # Lazily generated and cached on first request, not computed
    # automatically at upload time like the embedding -- LLM API calls
    # are the scarce resource here (free-tier rate limits), unlike
    # local embedding generation, so we only pay that cost when someone
    # actually asks for it, once.
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    improvement_suggestions: Mapped[Optional[list[str]]] = mapped_column(JSON, nullable=True)

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
