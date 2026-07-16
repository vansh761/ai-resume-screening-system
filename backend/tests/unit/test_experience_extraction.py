"""Unit tests for years-of-experience extraction."""

import pytest

from app.ai.experience_extraction import extract_years_experience


@pytest.mark.unit
def test_extracts_simple_years_mention() -> None:
    assert extract_years_experience("5 years of experience in software development") == 5.0


@pytest.mark.unit
def test_extracts_plus_notation() -> None:
    assert extract_years_experience("8+ years experience") == 8.0


@pytest.mark.unit
def test_takes_maximum_of_multiple_mentions() -> None:
    text = "3 years of Python experience. 7 years of overall industry experience."
    assert extract_years_experience(text) == 7.0


@pytest.mark.unit
def test_returns_none_when_no_experience_mentioned() -> None:
    assert extract_years_experience("Skilled software engineer with a passion for clean code") is None


@pytest.mark.unit
def test_returns_none_for_empty_text() -> None:
    assert extract_years_experience("") is None


@pytest.mark.unit
def test_rejects_implausible_values() -> None:
    """A stray '404 years' (e.g., from a mis-matched ID number) should be filtered out."""
    assert extract_years_experience("Error code 404 years old system") is None
