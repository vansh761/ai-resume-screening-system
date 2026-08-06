"""
FAISS-based semantic similarity search.

Design decision
----------------
The index is assembled fresh, in-memory, on every search call — not
persisted to disk or maintained incrementally as resumes are added or
removed. This is deliberately the simpler of two valid designs (the
alternative being a persisted index file with incremental add/remove
operations), and it's the right choice at this project's scale:

- FAISS's `IndexFlatIP` (flat inner-product index) construction is
  near-instant even for tens of thousands of vectors — there's no
  meaningful latency cost to rebuilding it per search.
- It sidesteps an entire class of consistency bugs: a persisted index
  can drift out of sync with the database (a deleted resume whose
  vector wasn't removed from the index, for instance). Rebuilding from
  the database's current state on every search makes that class of bug
  structurally impossible — the index is always a direct reflection of
  what's actually in the `resumes` table at query time.
- The genuinely expensive part — running text through the embedding
  model — already happened once, at upload time (see
  `app/ai/embeddings.py` and its use in `resume_service.py`). This
  module only does vector math on already-computed numbers, which is
  cheap.

This trades off scale: at a much larger number of resumes (hundreds of
thousands+), rebuilding on every search would eventually become the
bottleneck, and a persisted, incrementally-updated index (e.g. via
FAISS's `IndexIVFFlat` with periodic rebuilds, or a managed vector DB)
would be the right next step. Worth stating this limitation plainly
rather than pretending the simple approach scales indefinitely.

We use `IndexFlatIP` (inner product) rather than `IndexFlatL2`
(Euclidean distance) because our embeddings are L2-normalized at
generation time (see `embed_text`'s `normalize_embeddings=True`) — for
normalized vectors, inner product IS cosine similarity. This avoids a
separate normalization step at search time and makes the FAISS score
directly interpretable as a cosine similarity in [-1, 1].
"""

import uuid

import faiss
import numpy as np


class ResumeSimilarityIndex:
    """
    Wraps a FAISS flat inner-product index alongside the resume IDs
    each vector corresponds to, since FAISS itself only knows about
    integer positions, not our domain's UUIDs.
    """

    def __init__(self, resume_ids: list[uuid.UUID], embeddings: list[list[float]]):
        if len(resume_ids) != len(embeddings):
            raise ValueError("resume_ids and embeddings must be the same length")

        self.resume_ids = resume_ids
        if embeddings:
            dimension = len(embeddings[0])
            self._index = faiss.IndexFlatIP(dimension)
            vectors = np.array(embeddings, dtype="float32")
            self._index.add(vectors)
        else:
            self._index = None

    def search(self, query_embedding: list[float], top_k: int) -> list[tuple[uuid.UUID, float]]:
        """
        Returns up to `top_k` (resume_id, similarity_score) pairs,
        ordered from most to least similar.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        query_vector = np.array([query_embedding], dtype="float32")
        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query_vector, k)

        results: list[tuple[uuid.UUID, float]] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS pads with -1 if fewer than k results exist
                continue
            results.append((self.resume_ids[idx], float(score)))
        return results


def build_index(resume_ids: list[uuid.UUID], embeddings: list[list[float]]) -> ResumeSimilarityIndex:
    """Convenience constructor, kept as a function for a clean call site in the search service."""
    return ResumeSimilarityIndex(resume_ids, embeddings)
