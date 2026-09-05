"""
Explainable scoring engine.
"""

import re
from dataclasses import dataclass, field

from app.models.job import Job
from app.models.resume import EducationLevel, Resume

_EDUCATION_RANK = {level: idx for idx, level in enumerate(EducationLevel)}

SCORING_WEIGHTS = {
    "skills_match": 0.30,
    "experience_match": 0.15,
    "education_match": 0.10,
    "semantic_similarity": 0.20,
    "ats_score": 0.10,
    "resume_quality": 0.10,
    "certifications": 0.025,
    "projects": 0.025,
}

_SECTION_HEADERS = ["experience", "education", "skills", "summary", "projects", "certifications"]
_CERTIFICATION_KEYWORDS = re.compile(r"\bcertifi(?:ed|cation)s?\b", re.IGNORECASE)
_PROJECT_KEYWORDS = re.compile(r"\bproject(?:s)?\b", re.IGNORECASE)
_BULLET_PATTERN = re.compile(r"^[\s]*[•\-\*]\s+", re.MULTILINE)
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE_PATTERN = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


@dataclass
class ScoreBreakdown:
    skills_match_score: float
    experience_match_score: float
    education_match_score: float
    certification_score: float
    project_score: float
    ats_score: float
    resume_quality_score: float
    semantic_similarity_score: float
    overall_score: float
    explanation: dict = field(default_factory=dict)


def _score_skills_match(resume_skill_names, required_skills, preferred_skills):
    matched_required = resume_skill_names & required_skills
    matched_preferred = resume_skill_names & preferred_skills
    missing_required = required_skills - resume_skill_names

    required_ratio = len(matched_required) / len(required_skills) if required_skills else 1.0
    preferred_ratio = len(matched_preferred) / len(preferred_skills) if preferred_skills else 1.0

    score = (required_ratio * 0.7 + preferred_ratio * 0.3) * 100
    explanation = {
        "matched_required_skills": sorted(matched_required),
        "matched_preferred_skills": sorted(matched_preferred),
        "missing_required_skills": sorted(missing_required),
    }
    return score, explanation


def _score_experience_match(resume_years, min_years):
    if min_years <= 0:
        return 100.0, {"note": "Job specifies no minimum experience requirement."}
    if resume_years is None:
        return 0.0, {"note": "No years of experience could be extracted from the resume."}

    ratio = min(resume_years / min_years, 1.0)
    score = ratio * 100
    return score, {
        "resume_years_experience": resume_years,
        "job_min_years_required": min_years,
    }


def _score_education_match(resume_level, min_level):
    if min_level is None:
        return 100.0, {"note": "Job specifies no minimum education requirement."}
    if resume_level is None:
        return 0.0, {"note": "No education level could be extracted from the resume."}

    resume_rank = _EDUCATION_RANK[resume_level]
    min_rank = _EDUCATION_RANK[min_level]
    score = 100.0 if resume_rank >= min_rank else 0.0
    return score, {
        "resume_education_level": resume_level.value,
        "job_min_education_level": min_level.value,
    }


def _score_ats_compatibility(resume_text):
    if not resume_text:
        return 0.0, {"note": "No parsed text available to evaluate."}

    lower_text = resume_text.lower()
    headers_found = [h for h in _SECTION_HEADERS if h in lower_text]
    has_email = bool(_EMAIL_PATTERN.search(resume_text))
    has_phone = bool(_PHONE_PATTERN.search(resume_text))
    word_count = len(resume_text.split())
    length_ok = 150 <= word_count <= 2000

    points = 0
    points += min(len(headers_found), 4) * 15
    points += 15 if has_email else 0
    points += 10 if has_phone else 0
    points += 15 if length_ok else 0
    score = min(points, 100)

    return float(score), {
        "section_headers_found": headers_found,
        "has_email": has_email,
        "has_phone": has_phone,
        "word_count": word_count,
    }


def _score_resume_quality(resume_text):
    if not resume_text:
        return 0.0, {"note": "No parsed text available to evaluate."}

    bullet_count = len(_BULLET_PATTERN.findall(resume_text))
    word_count = len(resume_text.split())

    points = 0
    points += min(bullet_count, 10) * 5
    points += 30 if 150 <= word_count <= 1500 else 10
    points += 20
    score = min(points, 100)

    return float(score), {"bullet_point_count": bullet_count, "word_count": word_count}


def _score_keyword_presence(resume_text, pattern):
    if not resume_text:
        return 0.0, {"note": "No parsed text available to evaluate."}
    mention_count = len(pattern.findall(resume_text))
    score = min(mention_count * 25, 100.0)
    return score, {"mention_count": mention_count}


def compute_score(resume: Resume, job: Job) -> ScoreBreakdown:
    resume_skill_names = {rs.skill.name for rs in resume.resume_skills}
    required_skill_names = {js.skill.name for js in job.job_skills if js.is_required}
    preferred_skill_names = {js.skill.name for js in job.job_skills if not js.is_required}

    skills_score, skills_explanation = _score_skills_match(
        resume_skill_names, required_skill_names, preferred_skill_names
    )
    experience_score, experience_explanation = _score_experience_match(
        resume.extracted_years_experience, job.min_experience_years
    )
    education_score, education_explanation = _score_education_match(
        resume.extracted_education_level, job.min_education_level
    )
    ats_score, ats_explanation = _score_ats_compatibility(resume.parsed_text or "")
    quality_score, quality_explanation = _score_resume_quality(resume.parsed_text or "")
    cert_score, cert_explanation = _score_keyword_presence(resume.parsed_text or "", _CERTIFICATION_KEYWORDS)
    project_score, project_explanation = _score_keyword_presence(resume.parsed_text or "", _PROJECT_KEYWORDS)

    semantic_score = 0.0
    semantic_explanation = {"note": "No embedding available for resume and/or job."}
    if resume.embedding and job.embedding:
        import numpy as np

        resume_vec = np.array(resume.embedding)
        job_vec = np.array(job.embedding)
        cosine_sim = float(
            np.dot(resume_vec, job_vec) / (np.linalg.norm(resume_vec) * np.linalg.norm(job_vec))
        )
        semantic_score = max(0.0, cosine_sim) * 100
        semantic_explanation = {"cosine_similarity": round(cosine_sim, 4)}

    overall = (
        skills_score * SCORING_WEIGHTS["skills_match"]
        + experience_score * SCORING_WEIGHTS["experience_match"]
        + education_score * SCORING_WEIGHTS["education_match"]
        + semantic_score * SCORING_WEIGHTS["semantic_similarity"]
        + ats_score * SCORING_WEIGHTS["ats_score"]
        + quality_score * SCORING_WEIGHTS["resume_quality"]
        + cert_score * SCORING_WEIGHTS["certifications"]
        + project_score * SCORING_WEIGHTS["projects"]
    )

    explanation = {
        "weights_used": SCORING_WEIGHTS,
        "skills_match": skills_explanation,
        "experience_match": experience_explanation,
        "education_match": education_explanation,
        "semantic_similarity": semantic_explanation,
        "ats_compatibility": ats_explanation,
        "resume_quality": quality_explanation,
        "certifications": cert_explanation,
        "projects": project_explanation,
    }

    return ScoreBreakdown(
        skills_match_score=round(skills_score, 2),
        experience_match_score=round(experience_score, 2),
        education_match_score=round(education_score, 2),
        certification_score=round(cert_score, 2),
        project_score=round(project_score, 2),
        ats_score=round(ats_score, 2),
        resume_quality_score=round(quality_score, 2),
        semantic_similarity_score=round(semantic_score, 2),
        overall_score=round(overall, 2),
        explanation=explanation,
    )
