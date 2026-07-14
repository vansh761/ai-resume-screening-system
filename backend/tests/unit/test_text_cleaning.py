"""Unit tests for text cleaning."""

import pytest

from app.ai.text_cleaning import clean_text


@pytest.mark.unit
def test_collapses_internal_whitespace() -> None:
    assert clean_text("Python    Developer") == "Python Developer"


@pytest.mark.unit
def test_collapses_excessive_blank_lines() -> None:
    raw = "Experience\n\n\n\n\nSkills"
    result = clean_text(raw)
    assert "\n\n\n" not in result
    assert "Experience" in result and "Skills" in result


@pytest.mark.unit
def test_strips_leading_and_trailing_whitespace() -> None:
    assert clean_text("   \n  Resume text  \n   ") == "Resume text"


@pytest.mark.unit
def test_empty_input_returns_empty_string() -> None:
    assert clean_text("") == ""
