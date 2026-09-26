"""
Unit tests for insights_service's caching behavior -- the core
guarantee this milestone depends on given free-tier rate limits: the
LLM is called at most once per resume/application, ever.
"""

from unittest.mock import patch

import pytest

from app.models.resume import FileType, Resume
from app.models.user import User, UserRole
from app.services.insights_service import get_or_generate_summary


def _make_resume_with_owner(db_session) -> Resume:
    candidate = User(
        email=f"insights-test-{id(db_session)}@example.com",
        hashed_password="x", full_name="Test Candidate", role=UserRole.CANDIDATE,
    )
    db_session.add(candidate)
    db_session.commit()

    resume = Resume(
        candidate_id=candidate.id,
        original_filename="r.pdf", storage_path="/x", file_type=FileType.PDF,
        parsed_text="Some resume content",
    )
    db_session.add(resume)
    db_session.commit()
    return resume


@pytest.mark.unit
def test_summary_is_generated_and_cached_on_first_call(db_session) -> None:
    resume = _make_resume_with_owner(db_session)

    with patch("app.services.insights_service.summarize_resume") as mock_summarize:
        mock_summarize.return_value = "Generated summary."
        result = get_or_generate_summary(db_session, resume)

        assert result == "Generated summary."
        assert resume.ai_summary == "Generated summary."
        mock_summarize.assert_called_once()


@pytest.mark.unit
def test_summary_is_not_regenerated_on_second_call(db_session) -> None:
    resume = _make_resume_with_owner(db_session)
    resume.ai_summary = "Already cached."
    db_session.commit()

    with patch("app.services.insights_service.summarize_resume") as mock_summarize:
        result = get_or_generate_summary(db_session, resume)

        assert result == "Already cached."
        mock_summarize.assert_not_called()
