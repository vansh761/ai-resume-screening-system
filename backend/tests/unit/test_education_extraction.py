"""Unit tests for education level extraction."""

import pytest

from app.ai.education_extraction import extract_education_level
from app.models.resume import EducationLevel


@pytest.mark.unit
def test_detects_bachelor_degree() -> None:
    assert extract_education_level("Bachelor's degree in Computer Science") == EducationLevel.BACHELOR


@pytest.mark.unit
def test_detects_master_degree() -> None:
    assert extract_education_level("M.Tech in Data Science from IIT") == EducationLevel.MASTER


@pytest.mark.unit
def test_detects_doctorate() -> None:
    assert extract_education_level("PhD in Machine Learning") == EducationLevel.DOCTORATE


@pytest.mark.unit
def test_returns_highest_level_when_multiple_present() -> None:
    text = "Bachelor's degree in Engineering, followed by a Master's degree in AI"
    assert extract_education_level(text) == EducationLevel.MASTER


@pytest.mark.unit
def test_returns_none_when_no_education_keywords() -> None:
    assert extract_education_level("Experienced professional with strong leadership skills") is None


@pytest.mark.unit
def test_returns_none_for_empty_text() -> None:
    assert extract_education_level("") is None
