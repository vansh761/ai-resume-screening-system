# AI Resume Screening System

A production-style internal recruitment platform: recruiters upload job descriptions,
candidates upload resumes, and the system parses, scores, ranks, and explains
candidate-job fit using an NLP + semantic search pipeline.

> **Status:** 🚧 Milestone 1 of 16 complete — architecture & scaffolding.
> See [docs/architecture](docs/architecture) for design docs as they're added.

## Why this exists

Most "resume screener" portfolio projects are a Jupyter notebook that computes
cosine similarity between two strings. This is not that. This project is built
the way an internal tool at a mid-size tech company would be: layered backend,
explainable scoring, background job processing, versioned APIs, and a real
test/CI pipeline.

## Tech Stack

| Layer | Choices |
|---|---|
| Backend | Python, FastAPI, SQLAlchemy, PostgreSQL |
| Caching / Queue | Redis, Celery |
| AI/NLP | Sentence-Transformers, spaCy, scikit-learn, FAISS, Hugging Face Transformers |
| Frontend | React, TypeScript, Tailwind CSS |
| Infra | Docker, Docker Compose, GitHub Actions |
| Testing | pytest (unit + integration) |

## Architecture

```
Client (React/TS)
      │ HTTPS
      ▼
FastAPI (versioned REST API, /api/v1)
      │
      ├──► PostgreSQL   (users, jobs, resumes, scores — system of record)
      ├──► Redis        (cache + Celery broker)
      └──► Celery workers (async: parsing, embedding generation, scoring)
```

The backend follows a **layered architecture**:

```
app/
├── api/        # HTTP layer: routers, request/response handling only
├── schemas/    # Pydantic request/response contracts
├── services/   # Business logic — framework-agnostic
├── models/     # SQLAlchemy ORM models (persistence layer)
├── ai/         # NLP/ML pipeline (parsing, embeddings, scoring)
├── workers/    # Celery task definitions
├── core/       # Config, logging, security — cross-cutting concerns
└── db/         # Database session/engine management
```

**Why layered?** Each layer depends only on the layer below it, never sideways
or upward. An API endpoint never talks to the database directly — it calls a
service, which uses a repository. This means we can swap PostgreSQL for
another store, or FAISS for a managed vector DB, by changing one layer without
touching the others (Dependency Inversion Principle in practice).

## Folder Structure (full repo)

```
ai-resume-screening-system/
├── backend/
│   ├── app/                  # application code (see above)
│   ├── tests/
│   │   ├── unit/             # fast, no external dependencies
│   │   └── integration/      # hits real DB/Redis via docker-compose
│   ├── alembic/               # DB migrations (added in Milestone 2)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
├── frontend/                  # React + TS + Tailwind (added in Milestone 12)
├── docs/
│   └── architecture/          # ADRs, diagrams — grows with each milestone
├── .github/workflows/         # CI pipelines (added in Milestone 15)
├── docker-compose.yml
├── .env.example
└── README.md
```

## Getting Started (local dev)

```bash
# 1. Clone and configure
cp .env.example .env
# edit .env — set SECRET_KEY and POSTGRES_PASSWORD

# 2. Start the stack
docker compose up --build

# 3. Verify it's alive
curl http://localhost:8010/health
# -> {"status": "ok", "environment": "development"}

# 4. API docs (Swagger UI)
open http://localhost:8010/api/v1/docs
```

> **Ports are configurable** (backend defaults to `8010`, Postgres to `5433`,
> Redis to `6380` on the host) to avoid clashing with other projects you
> might have running. Override via `BACKEND_PORT`, `POSTGRES_HOST_PORT`,
> `REDIS_HOST_PORT` in `.env` if you need something else. Inside the Docker
> network, services still talk to each other on their standard ports
> (5432, 6379) — only the host-side mapping changed.

## Running Tests

```bash
cd backend
pytest                          # all tests
pytest -m unit                  # fast unit tests only
pytest -m integration           # tests requiring DB/Redis
pytest --cov=app --cov-report=html   # coverage report
```

## Project Roadmap

| Milestone | Status |
|---|---|
| 1. Architecture & scaffolding | ✅ Done |
| 2. Database design | ⬜ Next |
| 3. Auth & RBAC | ⬜ |
| 4. Resume parsing pipeline | ⬜ |
| 5. NLP entity/skill extraction | ⬜ |
| 6. Embeddings + FAISS search | ⬜ |
| 7. Explainable scoring engine | ⬜ |
| 8. Ranking, clustering, dedup | ⬜ |
| 9. Summarization & recommendations | ⬜ |
| 10. Celery background pipeline | ⬜ |
| 11. API hardening | ⬜ |
| 12. React dashboard | ⬜ |
| 13. Analytics & export | ⬜ |
| 14. Test suite | ⬜ |
| 15. CI/CD | ⬜ |
| 16. Final docs | ⬜ |
