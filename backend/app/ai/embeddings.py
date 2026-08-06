"""
Sentence embedding generation.

Design decision
----------------
`all-MiniLM-L6-v2` was chosen over larger models (e.g. `all-mpnet-base-v2`)
for a specific, statable trade-off: it produces 384-dimensional vectors
at roughly 5x the inference speed with only a modest quality drop on
semantic similarity benchmarks. For resume-to-job matching, where we
care about broad thematic similarity ("this resume is about backend
engineering with cloud infra experience") rather than nuanced literary
subtlety, that trade-off favors the smaller model — especially in a
portfolio/demo context where fast iteration and a lighter Docker image
matter more than squeezing out the last percentage point of benchmark
accuracy.

The model is loaded once and cached at module level (`lru_cache`) —
loading a transformer model is expensive (reading weights off disk,
initializing the network); doing that once per process rather than
once per request is the whole reason embedding generation is fast in
practice.
"""

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    """
    Returns a cached SentenceTransformer instance.

    Cached rather than instantiated per call for the same reason
    `app/ai/skill_extraction.py` caches its blank spaCy pipeline: model
    loading cost should be paid once per process, not once per resume.
    """
    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


def embed_text(text: str) -> list[float]:
    """
    Generates a single embedding vector for `text`.

    Returns a plain Python list (not a numpy array) because this is
    what gets stored in the `Resume.embedding` JSON column — numpy
    arrays aren't JSON-serializable, and converting at the boundary
    here keeps that concern out of every caller.
    """
    model = get_embedding_model()
    vector: np.ndarray = model.encode(text, normalize_embeddings=True)
    return vector.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Generates embeddings for multiple texts in a single batched call.

    Batching matters here: encoding N texts one at a time means N
    separate forward passes; encoding them together lets the model
    exploit batch parallelism, which is meaningfully faster for
    anything beyond a handful of texts (e.g. rebuilding embeddings for
    every resume during a bulk re-processing job).
    """
    if not texts:
        return []
    model = get_embedding_model()
    vectors: np.ndarray = model.encode(texts, normalize_embeddings=True)
    return vectors.tolist()
