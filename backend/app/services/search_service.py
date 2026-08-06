"""
Semantic search service.

Given a job description (free text, submitted by a recruiter), finds
the most semantically similar resumes system-wide — this is the
"AI-powered candidate search" feature, and the first place in this
system where a recruiter interacts with anything beyond CRUD.

Deliberately scoped to search across ALL candidates' resumes, not just
one candidate's — unlike the resume upload/fetch endpoints (Milestone
4), which are correctly scoped to "your own resumes only". A recruiter
searching for candidates needs visibility across the whole candidate
pool; that's the entire point of the feature, not an oversight in
access control. Role enforcement (recruiter-only) happens at the API
layer via `require_role`, same as every other recruiter-only action.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import embed_text
from app.ai.faiss_index import build_index
from app.models.resume import Resume


def semantic_search_resumes(
    db: Session, job_description: str, top_k: int = 10
) -> list[tuple[Resume, float]]:
    """
    Returns up to `top_k` resumes most semantically similar to
    `job_description`, each paired with its cosine similarity score
    (higher is more similar; range is roughly [-1, 1] but in practice
    almost always positive for genuinely related text).

    Resumes with no stored embedding (upload still processing, or
    embedding generation failed — see `resume_service.upload_resume`)
    are excluded from the candidate pool entirely rather than being
    included with a fabricated score of 0, which would misleadingly
    rank them as "somewhat similar" instead of "not yet evaluable".
    """
    resumes_with_embeddings = db.execute(
        select(Resume).where(Resume.embedding.is_not(None))
    ).scalars().all()

    if not resumes_with_embeddings:
        return []

    resume_ids = [r.id for r in resumes_with_embeddings]
    embeddings = [r.embedding for r in resumes_with_embeddings]
    resumes_by_id = {r.id: r for r in resumes_with_embeddings}

    index = build_index(resume_ids, embeddings)
    query_embedding = embed_text(job_description)
    ranked_ids_with_scores = index.search(query_embedding, top_k)

    return [(resumes_by_id[resume_id], score) for resume_id, score in ranked_ids_with_scores]
