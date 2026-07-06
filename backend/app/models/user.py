"""
User model.

Represents both recruiters and candidates via a `role` discriminator
column (Single Table Inheritance) rather than two separate tables — see
the architecture discussion in Milestone 2's README section for the
reasoning and the trade-off being made deliberately here.
"""

import enum
import uuid
from typing import List

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    """
    Discriminates between the two user types in the system.

    Inherits from `str` so the enum serializes cleanly to JSON in API
    responses (`UserRole.RECRUITER` becomes `"recruiter"`, not an
    unserializable Python enum object).
    """

    RECRUITER = "recruiter"
    CANDIDATE = "candidate"


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A person who can log into the platform, as either a recruiter
    (posts jobs, reviews candidates) or a candidate (uploads resumes,
    applies to jobs).
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- Relationships ---
    # A recruiter's posted jobs. Empty for candidate-role users.
    jobs_posted: Mapped[List["Job"]] = relationship(
        back_populates="recruiter", cascade="all, delete-orphan"
    )
    # A candidate's uploaded resumes. Empty for recruiter-role users.
    resumes: Mapped[List["Resume"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
