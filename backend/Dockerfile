# --- Stage 1: build dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir --user -r requirements.txt

# --- Stage 2: runtime image ---
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN groupadd -r appuser && useradd -r -g appuser -m appuser

COPY --from=builder /root/.local /home/appuser/.local
COPY . .

RUN chown -R appuser:appuser /app /home/appuser
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Pre-download and cache the sentence-transformer model at BUILD time,
# not at first request/test run.
#
# Why this matters: without this step, the first time
# `get_embedding_model()` runs (whether that's a real API request or
# the very first `pytest` run) triggers a ~80MB download from
# HuggingFace's model hub. That means: (1) the first API call after a
# fresh deploy is unexpectedly slow and network-dependent, and (2) test
# runs require internet access and add real latency to CI. Baking the
# model into the image layer means it's already on disk before the
# container ever starts serving traffic -- a genuinely "production"
# habit, not just a convenience.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
