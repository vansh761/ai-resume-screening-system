"""Score model - the explainable, multi-factor scoring result."""

import uuid

from sqlalchemy import Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin

JSONVariant = JSON().with_variant(JSONB(), "postgresql")


class Score(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "scores"

    application_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("applications.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    skills_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    experience_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    education_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    certification_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    project_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ats_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    resume_quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    semantic_similarity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    explanation: Mapped[dict] = mapped_column(JSONVariant, default=dict, nullable=False)

    application: Mapped["Application"] = relationship(back_populates="score")

    def __repr__(self) -> str:
        return f"<Score application_id={self.application_id} overall={self.overall_score}>"
