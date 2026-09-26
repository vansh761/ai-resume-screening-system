"""
Unit tests for the insight-generation functions, with the LLM client
mocked -- these test our prompt construction and response parsing
logic, not Gemini's actual output quality (that's what the one real
end-to-end test in test_insights_flow.py is for). Mocking here keeps
the fast unit-test tier free of external API calls and quota usage.
"""

from unittest.mock import patch

import pytest

from app.ai.llm_client import LLMGenerationError
from app.ai.resume_insights import (
    generate_interview_questions,
    suggest_resume_improvements,
    summarize_resume,
)


@pytest.mark.unit
def test_summarize_resume_returns_summary_from_response() -> None:
    with patch("app.ai.resume_insights.generate_json") as mock_generate:
        mock_generate.return_value = {"summary": "A skilled backend engineer."}
        result = summarize_resume("some resume text")
        assert result == "A skilled backend engineer."


@pytest.mark.unit
def test_summarize_resume_raises_on_missing_key() -> None:
    with patch("app.ai.resume_insights.generate_json") as mock_generate:
        mock_generate.return_value = {"wrong_key": "oops"}
        with pytest.raises(LLMGenerationError):
            summarize_resume("some resume text")


@pytest.mark.unit
def test_summarize_resume_propagates_llm_errors() -> None:
    with patch("app.ai.resume_insights.generate_json") as mock_generate:
        mock_generate.side_effect = LLMGenerationError("rate limited")
        with pytest.raises(LLMGenerationError):
            summarize_resume("some resume text")


@pytest.mark.unit
def test_generate_interview_questions_returns_list() -> None:
    with patch("app.ai.resume_insights.generate_json") as mock_generate:
        mock_generate.return_value = {"questions": ["Q1?", "Q2?", "Q3?", "Q4?", "Q5?"]}
        result = generate_interview_questions("resume text", "job description")
        assert len(result) == 5
        assert result[0] == "Q1?"


@pytest.mark.unit
def test_suggest_resume_improvements_returns_list() -> None:
    with patch("app.ai.resume_insights.generate_json") as mock_generate:
        mock_generate.return_value = {"suggestions": ["Add metrics", "Fix formatting"]}
        result = suggest_resume_improvements("resume text")
        assert result == ["Add metrics", "Fix formatting"]
