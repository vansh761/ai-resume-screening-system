# --- Stage 1: build dependencies ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only PyTorch FIRST, from PyTorch's own CPU wheel index.
# Why: sentence-transformers depends on torch>=1.11.0 with no upper
# bound, and pip's default resolver on Linux picks the CUDA-enabled
# build (500MB+ torch, plus gigabytes of NVIDIA CUDA libraries) even
# though this container has no GPU and never will. Installing the
# small CPU-only wheel here means when sentence-transformers is
# installed next, pip sees torch's version constraint is already
# satisfied and never attempts the CUDA download at all.
RUN pip install --no-cache-dir --user --default-timeout=1000 \
    torch==2.3.1+cpu --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir --user --default-timeout=1000 -r requirements.txt

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

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
