"""Unit tests for skill extraction (no DB needed for the name-matching core logic)."""

import pytest

from app.ai.skill_extraction import extract_skill_names

SKILL_VOCAB = ["Python", "FastAPI", "PostgreSQL", "Docker", "React", "C++"]


@pytest.mark.unit
def test_extracts_exact_matches() -> None:
    text = "Experienced with Python, FastAPI, and PostgreSQL for backend development."
    result = extract_skill_names(text, SKILL_VOCAB)
    assert result == {"Python", "FastAPI", "PostgreSQL"}


@pytest.mark.unit
def test_matching_is_case_insensitive() -> None:
    text = "worked with PYTHON and docker daily"
    result = extract_skill_names(text, SKILL_VOCAB)
    assert result == {"Python", "Docker"}


@pytest.mark.unit
def test_no_false_positive_on_unrelated_text() -> None:
    text = "Managed a team of five people and improved customer satisfaction."
    result = extract_skill_names(text, SKILL_VOCAB)
    assert result == set()


@pytest.mark.unit
def test_duplicate_mentions_deduplicated() -> None:
    text = "Python developer. Python expert. Extensive Python experience."
    result = extract_skill_names(text, SKILL_VOCAB)
    assert result == {"Python"}


@pytest.mark.unit
def test_empty_text_returns_empty_set() -> None:
    assert extract_skill_names("", SKILL_VOCAB) == set()
