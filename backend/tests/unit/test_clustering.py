"""Unit tests for k-means clustering over embeddings."""

import pytest

from app.ai.clustering import choose_cluster_count, cluster_embeddings


@pytest.mark.unit
def test_choose_cluster_count_scales_with_sample_size() -> None:
    assert choose_cluster_count(3) == 1
    assert choose_cluster_count(9) == 3
    assert choose_cluster_count(100) == 6  # capped at max_clusters default


@pytest.mark.unit
def test_choose_cluster_count_handles_tiny_pools() -> None:
    assert choose_cluster_count(0) == 1
    assert choose_cluster_count(1) == 1


@pytest.mark.unit
def test_cluster_embeddings_groups_similar_vectors_together() -> None:
    # Two obvious groups: points near (0,0) and points near (10,10).
    embeddings = [
        [0.0, 0.0], [0.1, 0.1], [0.2, -0.1],
        [10.0, 10.0], [10.1, 9.9], [9.9, 10.2],
    ]
    labels = cluster_embeddings(embeddings, n_clusters=2)

    assert len(labels) == 6
    # The first three should share a label, the last three should
    # share a (different) label.
    assert labels[0] == labels[1] == labels[2]
    assert labels[3] == labels[4] == labels[5]
    assert labels[0] != labels[3]


@pytest.mark.unit
def test_cluster_embeddings_empty_input_returns_empty_list() -> None:
    assert cluster_embeddings([]) == []


@pytest.mark.unit
def test_cluster_embeddings_n_clusters_capped_at_sample_size() -> None:
    embeddings = [[0.0, 0.0], [1.0, 1.0]]
    labels = cluster_embeddings(embeddings, n_clusters=10)
    assert len(set(labels)) <= 2
