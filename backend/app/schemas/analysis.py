"""Pydantic schemas for clustering, duplicate detection, and similar-candidate recommendations."""

import uuid

from pydantic import BaseModel


class ClusterResult(BaseModel):
    cluster_id: int
    label: str
    size: int
    resume_ids: list[uuid.UUID]


class DuplicatePair(BaseModel):
    resume_a_id: uuid.UUID
    resume_a_filename: str
    resume_b_id: uuid.UUID
    resume_b_filename: str
    similarity: float


class SimilarResumeResult(BaseModel):
    resume_id: uuid.UUID
    candidate_name: str
    original_filename: str
    similarity_score: float
