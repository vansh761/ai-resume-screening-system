"""
Unit tests for the FAISS similarity index.

These use small, hand-constructed vectors rather than real embeddings
— the index's job is pure vector math (find nearest neighbors by
inner product), which is fully testable without any model dependency.
Testing it in isolation from `embeddings.py` keeps these tests fast
and keeps the two concerns (vector math vs. text-to-vector conversion)
independently verifiable.
"""

import uuid

import pytest

from app.ai.faiss_index import build_index


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


@pytest.mark.unit
def test_search_returns_most_similar_vector_first() -> None:
    id_a, id_b, id_c = _uuid(), _uuid(), _uuid()
    # Simple 2D vectors for readability: a and the query point in
    # nearly the same direction, b is orthogonal, c points opposite.
    embeddings = [
        [1.0, 0.0],   # id_a: same direction as query
        [0.0, 1.0],   # id_b: orthogonal
        [-1.0, 0.0],  # id_c: opposite direction
    ]
    index = build_index([id_a, id_b, id_c], embeddings)

    results = index.search(query_embedding=[1.0, 0.0], top_k=3)

    assert results[0][0] == id_a
    assert results[-1][0] == id_c


@pytest.mark.unit
def test_search_respects_top_k() -> None:
    ids = [_uuid() for _ in range(5)]
    embeddings = [[float(i), 0.0] for i in range(5)]
    index = build_index(ids, embeddings)

    results = index.search(query_embedding=[4.0, 0.0], top_k=2)

    assert len(results) == 2


@pytest.mark.unit
def test_search_on_empty_index_returns_empty_list() -> None:
    index = build_index([], [])
    results = index.search(query_embedding=[1.0, 0.0], top_k=5)
    assert results == []


@pytest.mark.unit
def test_top_k_larger_than_available_vectors_returns_all() -> None:
    ids = [_uuid(), _uuid()]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    index = build_index(ids, embeddings)

    results = index.search(query_embedding=[1.0, 0.0], top_k=50)

    assert len(results) == 2


@pytest.mark.unit
def test_mismatched_lengths_raises() -> None:
    with pytest.raises(ValueError):
        build_index([_uuid(), _uuid()], [[1.0, 0.0]])
