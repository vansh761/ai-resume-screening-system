"""Pydantic schemas for the recruiter-facing semantic search endpoint."""

import uuid

from pydantic import BaseModel, Field


class ResumeSearchRequest(BaseModel):
    """
    Request body for POST /search/resumes.

    `top_k` is bounded (1-50) rather than unbounded — an unbounded
    value would let a caller request the entire resume table sorted by
    similarity in one request, which is both a performance foot-gun and
    unnecessary: nobody reviewing search results actually needs more
    than a few dozen ranked candidates at once. Pagination properly
    belongs to Milestone 11, but this cap prevents the worst case in
    the meantime.
    """

    job_description: str = Field(min_length=10, max_length=10_000)
    top_k: int = Field(default=10, ge=1, le=50)


class ResumeSearchResult(BaseModel):
    """A single ranked resume result, with the score that produced its rank."""

    resume_id: uuid.UUID
    candidate_name: str
    original_filename: str
    similarity_score: float
    matched_skills: list[str]
