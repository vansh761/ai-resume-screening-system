"""Pydantic schemas for resume upload and retrieval."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.resume import EducationLevel, FileType


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_type: FileType
    parsed_text: Optional[str]
    created_at: datetime
    extracted_skills: list[str] = []
    years_experience: Optional[float] = None
    education_level: Optional[EducationLevel] = None


class ResumeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    file_type: FileType
    created_at: datetime
    has_parsed_text: bool = False
