"""
Candidate analysis endpoints: clustering, duplicate detection, and
similar-candidate recommendations. All recruiter-only -- these are
recruiting-workflow tools, not something a candidate has a legitimate
use for.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.analysis import ClusterResult, DuplicatePair, SimilarResumeResult
from app.services.candidate_analysis_service import (
    cluster_applicants_for_job,
    find_duplicate_resumes,
    find_similar_resumes,
)
from app.services.job_service import get_job
from app.services.resume_service import get_resume_for_candidate

router = APIRouter(prefix="/analysis", tags=["Candidate Analysis"])


@router.get("/jobs/{job_id}/clusters", response_model=list[ClusterResult])
def cluster_applicants(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> list[ClusterResult]:
    """
    Groups a job's applicants into clusters by resume similarity, each
    labeled by its members' most common skills -- e.g. surfaces "these
    12 applicants are all frontend-leaning" as a group a recruiter
    might not have thought to filter for explicitly.
    """
    job = get_job(db, job_id)
    if job is None or job.recruiter_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    clusters = cluster_applicants_for_job(db, job_id)
    return [ClusterResult(**c) for c in clusters]


@router.get("/duplicates", response_model=list[DuplicatePair])
def detect_duplicates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> list[DuplicatePair]:
    """
    Flags near-identical resumes system-wide -- same candidate
    re-uploading, or heavily templated resumes. See
    `app/ai/duplicate_detection.py` for the stated O(n^2) scale limit.
    """
    duplicates = find_duplicate_resumes(db)
    return [DuplicatePair(**d) for d in duplicates]


@router.get("/resumes/{resume_id}/similar", response_model=list[SimilarResumeResult])
def similar_resumes(
    resume_id: uuid.UUID,
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> list[SimilarResumeResult]:
    """
    "Candidates similar to this one" -- a recruiter viewing a strong
    candidate can immediately see who else resembles them, reusing the
    Milestone 6 FAISS search machinery with this resume as the query.
    """
    # Note: recruiters can look up any resume by ID here (not scoped to
    # a candidate owner) -- this is intentional, mirroring the search
    # endpoint's system-wide visibility for recruiter-facing analysis
    # tools, unlike the candidate-scoped resume endpoints in Milestone 4.
    from app.models.resume import Resume

    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    ranked = find_similar_resumes(db, resume, top_k)
    return [
        SimilarResumeResult(
            resume_id=r.id,
            candidate_name=r.candidate.full_name,
            original_filename=r.original_filename,
            similarity_score=round(score, 4),
        )
        for r, score in ranked
    ]
