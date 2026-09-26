"""
Insights service: orchestrates lazy generation + caching of
LLM-powered summary, improvement suggestions, and interview questions.

Every function follows the same shape: return the cached value if
present, otherwise generate, persist, and return it. This means the
expensive (and rate-limited) LLM call only ever happens once per
resume/application, no matter how many times the data is viewed.
"""

from sqlalchemy.orm import Session

from app.ai.llm_client import LLMGenerationError
from app.ai.resume_insights import (
    generate_interview_questions,
    suggest_resume_improvements,
    summarize_resume,
)
from app.models.application import Application
from app.models.resume import Resume


def get_or_generate_summary(db: Session, resume: Resume) -> str:
    if resume.ai_summary is not None:
        return resume.ai_summary

    summary = summarize_resume(resume.parsed_text or "")
    resume.ai_summary = summary
    db.commit()
    db.refresh(resume)
    return summary


def get_or_generate_improvement_suggestions(db: Session, resume: Resume) -> list[str]:
    if resume.improvement_suggestions is not None:
        return resume.improvement_suggestions

    suggestions = suggest_resume_improvements(resume.parsed_text or "")
    resume.improvement_suggestions = suggestions
    db.commit()
    db.refresh(resume)
    return suggestions


def get_or_generate_interview_questions(db: Session, application: Application) -> list[str]:
    if application.interview_questions is not None:
        return application.interview_questions

    questions = generate_interview_questions(
        application.resume.parsed_text or "", application.job.description
    )
    application.interview_questions = questions
    db.commit()
    db.refresh(application)
    return questions
