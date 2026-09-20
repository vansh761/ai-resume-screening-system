"""
Resume clustering via k-means over embeddings.

Design decision
----------------
Clustering happens over a job's applicant pool, not the entire system's
resumes -- "show me the natural groups among these 40 applicants" is
an actionable recruiter workflow; "cluster every resume in the whole
database" isn't tied to any specific decision a recruiter needs to
make.

Cluster count (k) selection uses a simple heuristic rather than the
elbow method or silhouette analysis. That's a deliberate trade-off,
not an oversight: those techniques add real value when you're
uncertain about natural structure in large, high-dimensional datasets.
At the scale this system actually operates in -- typically dozens of
applicants per job, not thousands -- a simple heuristic is honest
about what it is and sufficient for the job. Over-engineering this
would cost real complexity for no practical benefit at this data size.
"""

import numpy as np
from sklearn.cluster import KMeans


def choose_cluster_count(n_samples: int, max_clusters: int = 6) -> int:
    """
    Picks a reasonable default cluster count from the sample size alone.

    Roughly one cluster per 3-4 samples, capped at `max_clusters` --
    small applicant pools (fewer than ~6) get very few clusters, since
    there's not enough data to meaningfully segment further.
    """
    if n_samples <= 1:
        return 1
    return max(1, min(max_clusters, n_samples // 3 or 1))


def cluster_embeddings(embeddings: list[list[float]], n_clusters: int | None = None) -> list[int]:
    """
    Returns a cluster label (0-indexed integer) for each embedding, in
    the same order as the input list.
    """
    if not embeddings:
        return []

    n_clusters = n_clusters or choose_cluster_count(len(embeddings))
    n_clusters = min(n_clusters, len(embeddings))

    if n_clusters <= 1:
        return [0] * len(embeddings)

    vectors = np.array(embeddings)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(vectors)
    return labels.tolist()
