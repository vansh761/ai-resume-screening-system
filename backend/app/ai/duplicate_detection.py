"""
Near-duplicate resume detection via pairwise cosine similarity.

Design decision
----------------
This is a brute-force O(n^2) comparison across every pair of resumes.
Explicitly stated limitation: this is fine at portfolio scale
(hundreds of resumes -- tens of thousands of comparisons, trivial),
and explicitly NOT fine at real production scale (millions of resumes,
where n^2 comparisons becomes computationally infeasible). A
production system at that scale would use locality-sensitive hashing
or an approximate-nearest-neighbor index to avoid the full pairwise
comparison. Naming this trade-off directly is more valuable than
pretending the simple approach scales indefinitely.

The threshold (0.97) is deliberately high -- this flags near-identical
content (the same resume uploaded twice, or a heavily templated
resume reused with minor edits), not merely "similar career field."
Two backend engineers' resumes will naturally share high similarity
without being duplicates; 0.97 is calibrated to catch actual content
duplication, not topical overlap.
"""

import numpy as np

DEFAULT_DUPLICATE_THRESHOLD = 0.97


def find_duplicate_pairs(
    resume_ids: list, embeddings: list[list[float]], threshold: float = DEFAULT_DUPLICATE_THRESHOLD
) -> list[tuple]:
    """
    Returns (resume_id_a, resume_id_b, similarity) tuples for every
    pair of resumes whose embeddings exceed `threshold`.
    """
    if len(resume_ids) < 2:
        return []

    vectors = np.array(embeddings)
    norms = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    similarity_matrix = norms @ norms.T

    pairs = []
    n = len(resume_ids)
    for i in range(n):
        for j in range(i + 1, n):
            sim = float(similarity_matrix[i][j])
            if sim >= threshold:
                pairs.append((resume_ids[i], resume_ids[j], round(sim, 4)))
    return pairs
