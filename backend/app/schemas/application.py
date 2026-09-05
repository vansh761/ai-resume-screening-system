"""Pydantic schemas for applications and their explainable scores."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.application import ApplicationStatus


class ApplicationCreate(BaseModel):
    job_id: uuid.UUID
    resume_id: uuid.UUID


class ScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skills_match_score: float
    experience_match_score: float
    education_match_score: float
    certification_score: float
    project_score: float
    ats_score: float
    resume_quality_score: float
    semantic_similarity_score: float
    overall_score: float
    explanation: dict


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    resume_id: uuid.UUID
    status: ApplicationStatus
    created_at: datetime
    score: ScoreRead | None = None
