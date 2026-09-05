"""Pydantic schemas for job postings."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobStatus
from app.models.resume import EducationLevel


class JobCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=10)
    min_experience_years: int = Field(default=0, ge=0, le=50)
    min_education_level: Optional[EducationLevel] = None
    department: Optional[str] = None
    location: Optional[str] = None
    required_skills: list[str] = []
    preferred_skills: list[str] = []


class JobStatusUpdate(BaseModel):
    status: JobStatus


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str
    department: Optional[str]
    location: Optional[str]
    min_experience_years: int
    min_education_level: Optional[EducationLevel]
    status: JobStatus
    created_at: datetime
    required_skills: list[str] = []
    preferred_skills: list[str] = []
