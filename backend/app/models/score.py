"""
Score model — the explainable, multi-factor scoring result for a single
application. Built in Milestone 2's schema now; the actual scoring
algorithm that populates these fields comes in Milestone 7.

Design decision
----------------
Every individual factor (skills match, experience match, etc.) is its
own column rather than a single opaque `overall_score` float. This is
the schema-level foundation of the "recruiter must understand exactly
why a candidate received a score" requirement — you cannot explain a
score after the fact if you never stored its components.

`explanation` is a JSON column holding structured, human-readable
reasoning (e.g. which specific skills matched/were missing, which
experience years were counted) — the numeric columns answer "what was
the score," the JSON column answers "why."
"""

import uuid

from sqlalchemy import Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin

# Use native JSONB on Postgres (supports indexing and containment queries
# like `explanation @> '{"missing_skills": ["kubernetes"]}'`), but fall
# back to plain JSON on any other dialect. This is what lets our unit
# tests run against fast in-memory SQLite while production still gets
# Postgres's richer JSON features — one column definition, two backends.
JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class Score(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """The scoring breakdown for exactly one application (1:1)."""

    __tablename__ = "scores"

    application_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("applications.id", ondelete="CASCADE"),
        unique=True,  # Enforces the 1:1 relationship at the DB level.
        nullable=False,
    )

    # --- Individual scoring factors (0.0 - 100.0 each) ---
    skills_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    experience_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    education_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    certification_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    project_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ats_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resume_quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    semantic_similarity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # --- Weighted composite (computed by the Milestone 7 scoring engine) ---
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # --- Structured explanation, e.g.:
    # {
    #   "matched_skills": ["python", "docker"],
    #   "missing_skills": ["kubernetes"],
    #   "experience_years_found": 3.5,
    #   "weights_used": {"skills": 0.3, "experience": 0.2, ...}
    # }
    explanation: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)

    # --- Relationships ---
    application: Mapped["Application"] = relationship(back_populates="score")

    def __repr__(self) -> str:
        return f"<Score application_id={self.application_id} overall={self.overall_score}>"
