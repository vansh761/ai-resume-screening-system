"""
Unit tests for embedding generation.

These tests load the real `all-MiniLM-L6-v2` model (pre-cached at
Docker build time — see the Dockerfile — so this doesn't trigger a
network download during test runs). We deliberately test against the
real model rather than mocking it: the entire point of an embedding
function is that semantically similar text produces similar vectors,
and a mock can't tell us whether that property actually holds.
"""

import numpy as np
import pytest

from app.ai.embeddings import embed_text, embed_texts


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


@pytest.mark.unit
def test_embedding_has_expected_dimension() -> None:
    vector = embed_text("Python backend developer")
    assert len(vector) == 384


@pytest.mark.unit
def test_similar_texts_have_higher_similarity_than_dissimilar_texts() -> None:
    """
    The core property that makes embeddings useful for this system at
    all: semantically related text should score higher than unrelated
    text. This is the test that would fail if we'd accidentally wired
    up a broken or randomly-initialized model.
    """
    query = embed_text("Python backend developer with FastAPI experience")
    similar = embed_text("Experienced Python engineer skilled in building REST APIs")
    dissimilar = embed_text("Professional chef specializing in French pastry")

    similarity_to_similar = _cosine_similarity(query, similar)
    similarity_to_dissimilar = _cosine_similarity(query, dissimilar)

    assert similarity_to_similar > similarity_to_dissimilar


@pytest.mark.unit
def test_identical_text_has_similarity_of_one() -> None:
    vector = embed_text("Data scientist with machine learning expertise")
    # Same text embedded twice should be numerically identical (or as
    # close as floating point allows) -- the model is deterministic.
    vector_again = embed_text("Data scientist with machine learning expertise")
    assert _cosine_similarity(vector, vector_again) == pytest.approx(1.0, abs=1e-5)


@pytest.mark.unit
def test_embed_texts_batches_correctly() -> None:
    texts = ["Python developer", "Java engineer", "Marketing manager"]
    vectors = embed_texts(texts)
    assert len(vectors) == 3
    assert all(len(v) == 384 for v in vectors)


@pytest.mark.unit
def test_embed_texts_empty_list_returns_empty_list() -> None:
    assert embed_texts([]) == []
