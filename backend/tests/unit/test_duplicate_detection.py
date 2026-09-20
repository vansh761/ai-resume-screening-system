"""Unit tests for near-duplicate resume detection."""

import uuid

import pytest

from app.ai.duplicate_detection import find_duplicate_pairs


@pytest.mark.unit
def test_identical_vectors_are_flagged_as_duplicates() -> None:
    id_a, id_b = uuid.uuid4(), uuid.uuid4()
    embeddings = [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]]
    pairs = find_duplicate_pairs([id_a, id_b], embeddings)

    assert len(pairs) == 1
    assert pairs[0][0] == id_a
    assert pairs[0][1] == id_b
    assert pairs[0][2] == pytest.approx(1.0)


@pytest.mark.unit
def test_dissimilar_vectors_are_not_flagged() -> None:
    id_a, id_b = uuid.uuid4(), uuid.uuid4()
    embeddings = [[1.0, 0.0], [0.0, 1.0]]  # orthogonal
    pairs = find_duplicate_pairs([id_a, id_b], embeddings)
    assert pairs == []


@pytest.mark.unit
def test_threshold_is_respected() -> None:
    id_a, id_b = uuid.uuid4(), uuid.uuid4()
    # A moderate similarity that shouldn't clear a strict threshold.
    embeddings = [[1.0, 0.3], [1.0, 0.0]]
    pairs_strict = find_duplicate_pairs([id_a, id_b], embeddings, threshold=0.999)
    pairs_loose = find_duplicate_pairs([id_a, id_b], embeddings, threshold=0.8)

    assert pairs_strict == []
    assert len(pairs_loose) == 1


@pytest.mark.unit
def test_single_resume_has_no_pairs() -> None:
    assert find_duplicate_pairs([uuid.uuid4()], [[1.0, 0.0]]) == []


@pytest.mark.unit
def test_finds_all_pairs_among_multiple_duplicates() -> None:
    """Three near-identical resumes should produce 3 pairs (all combinations)."""
    ids = [uuid.uuid4() for _ in range(3)]
    embeddings = [[1.0, 0.0, 0.0]] * 3
    pairs = find_duplicate_pairs(ids, embeddings)
    assert len(pairs) == 3
