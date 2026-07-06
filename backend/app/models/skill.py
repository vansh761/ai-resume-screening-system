"""
Skill model and its many-to-many association tables.

Design decision
----------------
`Skill` is a normalized lookup table rather than free-text strings
scattered across resumes and jobs. This is what makes "missing skills
detection" a clean set operation (job's required skills minus resume's
extracted skills) instead of fuzzy string matching every time, and it's
what lets us later add synonym handling (e.g. "JS" and "JavaScript"
resolving to the same Skill row) in exactly one place.

`ResumeSkill` and `JobSkill` are explicit association objects (not bare
`Table` objects) because `JobSkill` needs an extra attribute
(`is_required`) beyond the two foreign keys — SQLAlchemy requires a
mapped class, not a plain association table, whenever the link itself
carries data.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, GUID, TimestampMixin, UUIDPrimaryKeyMixin


class Skill(Base, UUIDPrimaryKeyMixin):
    """
    A single canonical skill (e.g. "Python", "AWS", "Project Management").

    `category` groups skills for UI filtering and analytics (e.g.
    "Programming Language", "Cloud Platform", "Soft Skill").
    """

    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("name", name="uq_skills_name"),)

    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="general")

    def __repr__(self) -> str:
        return f"<Skill name={self.name}>"


class ResumeSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Association: this skill was found on this resume (via NLP extraction
    in Milestone 5). One row per (resume, skill) pair.
    """

    __tablename__ = "resume_skills"
    __table_args__ = (UniqueConstraint("resume_id", "skill_id", name="uq_resume_skill"),)

    resume_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )

    resume: Mapped["Resume"] = relationship(back_populates="resume_skills")
    skill: Mapped["Skill"] = relationship()


class JobSkill(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Association: this skill is relevant to this job posting.

    `is_required` distinguishes a hard requirement ("must know Kubernetes")
    from a nice-to-have ("familiarity with Terraform a plus") — this
    distinction directly feeds the scoring engine's weighting in
    Milestone 7.
    """

    __tablename__ = "job_skills"
    __table_args__ = (UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),)

    job_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("skills.id", ondelete="CASCADE"), nullable=False
    )
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    job: Mapped["Job"] = relationship(back_populates="job_skills")
    skill: Mapped["Skill"] = relationship()
