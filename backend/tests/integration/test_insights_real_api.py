"""
Real, live test against the actual Gemini API -- not mocked. This is
deliberately excluded from the default `-m unit` test run (separate
marker) since it costs real API quota and requires network access and
a configured GEMINI_API_KEY. Run explicitly with:

    pytest -m llm_integration -v

This is the test that actually proves the Gemini integration works
end-to-end, as opposed to the mocked unit tests, which only prove our
own prompt/parsing code is correct.
"""

import pytest

from app.ai.resume_insights import summarize_resume
from app.core.config import settings


@pytest.mark.llm_integration
def test_summarize_resume_against_real_gemini_api() -> None:
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY not configured, skipping real API test")

    resume_text = (
        "Jane Doe is a Senior Backend Engineer with 6 years of experience "
        "building scalable APIs in Python and FastAPI. She has led teams "
        "deploying microservices on AWS and has a strong background in "
        "PostgreSQL database design."
    )

    summary = summarize_resume(resume_text)

    assert isinstance(summary, str)
    assert len(summary) > 20
    # Loose content check -- proves the model actually engaged with the
    # text rather than returning something generic/empty.
    assert "backend" in summary.lower() or "engineer" in summary.lower()
