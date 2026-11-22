"""
LLM-powered insights endpoints: resume summary, improvement
suggestions (both candidate-facing, scoped to the resume's owner --
same ownership pattern as Milestone 4's resume endpoints), and
interview questions (recruiter-facing, scoped to the job's owner --
same pattern as Milestone 7's application endpoints).

Every endpoint returns 503, not 500, when the LLM call fails -- this
correctly signals "the AI insight generation is temporarily
unavailable" (a real possibility given free-tier rate limits) rather
than looking like a bug in our own code.

Since Milestone 10, resume-based endpoints also return 409 while a
resume is still being processed (or failed to process): there's no
text to summarize yet, and sending an empty prompt would burn
rate-limited LLM quota and cache a meaningless result.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.llm_client import LLMGenerationError
from app.api.deps import require_role
from app.db.session import get_db
from app.models.resume import ProcessingStatus, Resume
from app.models.user import User, UserRole
from app.schemas.insights import (
    ImprovementSuggestionsRead,
    InterviewQuestionsRead,
    ResumeSummaryRead,
)
from app.services.application_service import get_application
from app.services.insights_service import (
    get_or_generate_improvement_suggestions,
    get_or_generate_interview_questions,
    get_or_generate_summary,
)
from app.services.resume_service import get_resume_for_candidate

router = APIRouter(prefix="/insights", tags=["Insights"])


def _require_processed(resume: Resume) -> None:
    """Raises 409 unless the resume's background processing has completed."""
    if resume.processing_status == ProcessingStatus.COMPLETED:
        return
    if resume.processing_status == ProcessingStatus.FAILED:
        detail = "This resume could not be processed. Please upload it again."
    else:
        detail = "This resume is still being processed. Try again shortly."
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


@router.get("/resumes/{resume_id}/summary", response_model=ResumeSummaryRead)
def get_resume_summary(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
) -> ResumeSummaryRead:
    resume = get_resume_for_candidate(db, resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    _require_processed(resume)

    try:
        summary = get_or_generate_summary(db, resume)
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI summary generation is temporarily unavailable: {exc}",
        )
    return ResumeSummaryRead(summary=summary)


@router.get("/resumes/{resume_id}/improvements", response_model=ImprovementSuggestionsRead)
def get_resume_improvements(
    resume_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
) -> ImprovementSuggestionsRead:
    resume = get_resume_for_candidate(db, resume_id, current_user.id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    _require_processed(resume)

    try:
        suggestions = get_or_generate_improvement_suggestions(db, resume)
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI improvement suggestions are temporarily unavailable: {exc}",
        )
    return ImprovementSuggestionsRead(suggestions=suggestions)


@router.get("/applications/{application_id}/interview-questions", response_model=InterviewQuestionsRead)
def get_interview_questions(
    application_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> InterviewQuestionsRead:
    application = get_application(db, application_id)
    if application is None or application.job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    try:
        questions = get_or_generate_interview_questions(db, application)
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"AI interview question generation is temporarily unavailable: {exc}",
        )
    return InterviewQuestionsRead(questions=questions)
