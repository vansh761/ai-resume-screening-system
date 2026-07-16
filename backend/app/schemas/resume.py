"""Pydantic schemas for resume upload and retrieval."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.resume import EducationLevel, FileType


class ResumeRead(BaseModel):
    """
    Public-facing resume representation.

    `storage_path` is deliberately NOT exposed here — it's an internal
    implementation detail (today: a local file path; later: an S3 key)
    that a client has no legitimate use for and that would leak
    information about our storage layout.

    `extracted_skills`, `years_experience`, and `education_level` are
    the Milestone 5 structured-extraction outputs. All three are
    nullable/empty when extraction hasn't run yet or found nothing —
    the API represents "we don't know" honestly rather than defaulting
    to a misleading empty value that looks the same as "we checked and
    found none."
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_type: FileType
    parsed_text: Optional[str]
    created_at: datetime  # represents upload time
    extracted_skills: list[str] = []
    years_experience: Optional[float] = None
    education_level: Optional[EducationLevel] = None


class ResumeSummary(BaseModel):
    """Lightweight representation for list views — omits full parsed_text."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_type: FileType
    created_at: datetime
    has_parsed_text: bool = False
