"""Pydantic schemas for LLM-generated resume insights."""

from pydantic import BaseModel


class ResumeSummaryRead(BaseModel):
    summary: str


class ImprovementSuggestionsRead(BaseModel):
    suggestions: list[str]


class InterviewQuestionsRead(BaseModel):
    questions: list[str]
