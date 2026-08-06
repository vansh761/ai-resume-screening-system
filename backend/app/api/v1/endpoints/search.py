"""
Semantic search endpoint.

Recruiter-only: submits a job description as free text and gets back
the most semantically similar resumes across the entire candidate
pool. This is intentionally decoupled from the `Job` model (Milestone
2's schema) for now -- Job CRUD endpoints don't exist yet (that's
Milestone 7's territory, alongside the scoring engine that will
consume both this similarity score and the structured skill/experience
data from Milestone 5). Accepting raw text here means the feature is
fully usable today and will plug directly into `Job.description` once
job posting endpoints exist, with no changes needed to the search
logic itself.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.search import ResumeSearchRequest, ResumeSearchResult
from app.services.search_service import semantic_search_resumes

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/resumes", response_model=list[ResumeSearchResult])
def search_resumes(
    request: ResumeSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> list[ResumeSearchResult]:
    """
    Ranks all embedded resumes by semantic similarity to the given job
    description. Resumes still pending embedding generation (freshly
    uploaded, or where embedding failed) are excluded from the pool --
    see `semantic_search_resumes`'s docstring for why.
    """
    ranked = semantic_search_resumes(db, request.job_description, request.top_k)

    return [
        ResumeSearchResult(
            resume_id=resume.id,
            candidate_name=resume.candidate.full_name,
            original_filename=resume.original_filename,
            similarity_score=round(score, 4),
            matched_skills=sorted(rs.skill.name for rs in resume.resume_skills),
        )
        for resume, score in ranked
    ]
