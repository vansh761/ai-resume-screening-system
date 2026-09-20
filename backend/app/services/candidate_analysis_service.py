"""
Candidate analysis service: clustering, duplicate detection, and
similar-candidate recommendations -- all built on the same embeddings
infrastructure from Milestone 6, applied to three different questions.
"""

import uuid
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.clustering import cluster_embeddings
from app.ai.duplicate_detection import find_duplicate_pairs
from app.ai.faiss_index import build_index
from app.models.application import Application
from app.models.resume import Resume


def _label_cluster(resumes: list[Resume]) -> str:
    """
    Builds a human-readable label from a cluster's most common skills,
    e.g. "Python, FastAPI, PostgreSQL" -- a numeric cluster ID alone
    ("Cluster 2") tells a recruiter nothing actionable; the skills
    that actually define the group do.
    """
    skill_counter: Counter[str] = Counter()
    for resume in resumes:
        for rs in resume.resume_skills:
            skill_counter[rs.skill.name] += 1

    top_skills = [name for name, _ in skill_counter.most_common(3)]
    return ", ".join(top_skills) if top_skills else "No common skills detected"


def cluster_applicants_for_job(db: Session, job_id: uuid.UUID) -> list[dict]:
    """
    Clusters every applicant to `job_id` by resume embedding
    similarity. Returns one entry per cluster: its label, size, and
    member resume IDs.

    Applicants whose resume has no embedding are excluded from
    clustering entirely (same reasoning as `semantic_search_resumes`:
    there's no vector to group them by, so silently placing them in an
    arbitrary cluster would misrepresent the analysis).
    """
    applications = db.execute(
        select(Application).where(Application.job_id == job_id)
    ).scalars().all()

    resumes = [app.resume for app in applications if app.resume.embedding is not None]
    if not resumes:
        return []

    embeddings = [r.embedding for r in resumes]
    labels = cluster_embeddings(embeddings)

    clusters: dict[int, list[Resume]] = {}
    for resume, label in zip(resumes, labels):
        clusters.setdefault(label, []).append(resume)

    return [
        {
            "cluster_id": cluster_id,
            "label": _label_cluster(members),
            "size": len(members),
            "resume_ids": [r.id for r in members],
        }
        for cluster_id, members in sorted(clusters.items())
    ]


def find_duplicate_resumes(db: Session) -> list[dict]:
    """
    Finds near-duplicate resumes system-wide (see
    `app/ai/duplicate_detection.py` for the O(n^2) scale caveat).
    Returns each pair with both resumes' owning candidate for context
    -- a recruiter (or admin) seeing "these two resumes are 98%
    identical" needs to know whose they are to act on it.
    """
    resumes_with_embeddings = db.execute(
        select(Resume).where(Resume.embedding.is_not(None))
    ).scalars().all()

    if len(resumes_with_embeddings) < 2:
        return []

    resume_ids = [r.id for r in resumes_with_embeddings]
    embeddings = [r.embedding for r in resumes_with_embeddings]
    resumes_by_id = {r.id: r for r in resumes_with_embeddings}

    duplicate_pairs = find_duplicate_pairs(resume_ids, embeddings)

    return [
        {
            "resume_a_id": id_a,
            "resume_a_filename": resumes_by_id[id_a].original_filename,
            "resume_b_id": id_b,
            "resume_b_filename": resumes_by_id[id_b].original_filename,
            "similarity": similarity,
        }
        for id_a, id_b, similarity in duplicate_pairs
    ]


def find_similar_resumes(db: Session, resume: Resume, top_k: int = 5) -> list[tuple[Resume, float]]:
    """
    "Candidates similar to this one" -- reuses the exact same FAISS
    index machinery as job-description search (Milestone 6), just with
    a different query vector (this resume's own embedding instead of
    an embedded job description). The resume being queried is excluded
    from its own results.
    """
    if resume.embedding is None:
        return []

    other_resumes = db.execute(
        select(Resume).where(Resume.embedding.is_not(None), Resume.id != resume.id)
    ).scalars().all()

    if not other_resumes:
        return []

    resume_ids = [r.id for r in other_resumes]
    embeddings = [r.embedding for r in other_resumes]
    resumes_by_id = {r.id: r for r in other_resumes}

    index = build_index(resume_ids, embeddings)
    ranked = index.search(resume.embedding, top_k)

    return [(resumes_by_id[rid], score) for rid, score in ranked]
