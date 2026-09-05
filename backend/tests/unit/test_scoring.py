"""
Unit tests for the scoring engine.
"""

import pytest

from app.ai.scoring import SCORING_WEIGHTS, compute_score
from app.models.job import Job
from app.models.resume import EducationLevel, FileType, Resume
from app.models.skill import JobSkill, ResumeSkill, Skill


def _skill(name: str) -> Skill:
    return Skill(name=name, category="test")


def _resume_with_skills(*skill_names: str, years=None, education=None, text="") -> Resume:
    resume = Resume(
        original_filename="r.pdf", storage_path="/x", file_type=FileType.PDF,
        parsed_text=text, extracted_years_experience=years, extracted_education_level=education,
    )
    resume.resume_skills = [ResumeSkill(skill=_skill(name)) for name in skill_names]
    return resume


def _job_with_skills(required: list[str], preferred: list[str] = None, min_years=0, min_education=None) -> Job:
    job = Job(title="Test Job", description="Test description", min_experience_years=min_years,
               min_education_level=min_education)
    job_skills = [JobSkill(skill=_skill(name), is_required=True) for name in required]
    job_skills += [JobSkill(skill=_skill(name), is_required=False) for name in (preferred or [])]
    job.job_skills = job_skills
    return job


@pytest.mark.unit
def test_weights_sum_to_one() -> None:
    assert sum(SCORING_WEIGHTS.values()) == pytest.approx(1.0)


@pytest.mark.unit
def test_perfect_skills_match_scores_full_marks() -> None:
    resume = _resume_with_skills("Python", "Docker")
    job = _job_with_skills(required=["Python", "Docker"])
    breakdown = compute_score(resume, job)
    assert breakdown.skills_match_score == 100.0
    assert breakdown.explanation["skills_match"]["missing_required_skills"] == []


@pytest.mark.unit
def test_missing_required_skill_reduces_score_and_is_named() -> None:
    resume = _resume_with_skills("Python")
    job = _job_with_skills(required=["Python", "Kubernetes"])
    breakdown = compute_score(resume, job)
    assert breakdown.skills_match_score < 100.0
    assert "Kubernetes" in breakdown.explanation["skills_match"]["missing_required_skills"]


@pytest.mark.unit
def test_experience_meeting_minimum_scores_full_marks() -> None:
    resume = _resume_with_skills(years=5.0)
    job = _job_with_skills(required=[], min_years=5)
    breakdown = compute_score(resume, job)
    assert breakdown.experience_match_score == 100.0


@pytest.mark.unit
def test_experience_below_minimum_scores_proportionally() -> None:
    resume = _resume_with_skills(years=3.0)
    job = _job_with_skills(required=[], min_years=6)
    breakdown = compute_score(resume, job)
    assert breakdown.experience_match_score == pytest.approx(50.0)


@pytest.mark.unit
def test_missing_experience_data_scores_zero_not_full_marks() -> None:
    resume = _resume_with_skills(years=None)
    job = _job_with_skills(required=[], min_years=3)
    breakdown = compute_score(resume, job)
    assert breakdown.experience_match_score == 0.0


@pytest.mark.unit
def test_job_with_no_experience_requirement_scores_full_marks_regardless() -> None:
    resume = _resume_with_skills(years=None)
    job = _job_with_skills(required=[], min_years=0)
    breakdown = compute_score(resume, job)
    assert breakdown.experience_match_score == 100.0


@pytest.mark.unit
def test_education_meeting_minimum_scores_full_marks() -> None:
    resume = _resume_with_skills(education=EducationLevel.MASTER)
    job = _job_with_skills(required=[], min_education=EducationLevel.BACHELOR)
    breakdown = compute_score(resume, job)
    assert breakdown.education_match_score == 100.0


@pytest.mark.unit
def test_education_below_minimum_scores_zero() -> None:
    resume = _resume_with_skills(education=EducationLevel.HIGH_SCHOOL)
    job = _job_with_skills(required=[], min_education=EducationLevel.BACHELOR)
    breakdown = compute_score(resume, job)
    assert breakdown.education_match_score == 0.0


@pytest.mark.unit
def test_semantic_similarity_is_zero_without_embeddings() -> None:
    resume = _resume_with_skills()
    resume.embedding = None
    job = _job_with_skills(required=[])
    job.embedding = None
    breakdown = compute_score(resume, job)
    assert breakdown.semantic_similarity_score == 0.0


@pytest.mark.unit
def test_semantic_similarity_uses_cosine_similarity_of_embeddings() -> None:
    resume = _resume_with_skills()
    resume.embedding = [1.0, 0.0]
    job = _job_with_skills(required=[])
    job.embedding = [1.0, 0.0]
    breakdown = compute_score(resume, job)
    assert breakdown.semantic_similarity_score == pytest.approx(100.0, abs=0.1)


@pytest.mark.unit
def test_ats_score_rewards_section_headers_and_contact_info() -> None:
    rich_text = (
        "Summary\nExperienced engineer.\n\nExperience\nBuilt things.\n\n"
        "Education\nBS in CS.\n\nSkills\nPython.\n\nContact: jane@example.com, +1 555-123-4567"
    )
    resume_rich = _resume_with_skills(text=rich_text * 10)
    resume_empty = _resume_with_skills(text="")
    job = _job_with_skills(required=[])

    breakdown_rich = compute_score(resume_rich, job)
    breakdown_empty = compute_score(resume_empty, job)

    assert breakdown_rich.ats_score > breakdown_empty.ats_score


@pytest.mark.unit
def test_overall_score_is_bounded_zero_to_hundred() -> None:
    resume = _resume_with_skills("Python", years=10, education=EducationLevel.DOCTORATE, text="Some resume text here")
    job = _job_with_skills(required=["Python"], min_years=1, min_education=EducationLevel.BACHELOR)
    breakdown = compute_score(resume, job)
    assert 0.0 <= breakdown.overall_score <= 100.0


@pytest.mark.unit
def test_explanation_includes_weights_used() -> None:
    resume = _resume_with_skills()
    job = _job_with_skills(required=[])
    breakdown = compute_score(resume, job)
    assert breakdown.explanation["weights_used"] == SCORING_WEIGHTS
