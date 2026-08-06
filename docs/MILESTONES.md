# Project Milestones Log

The build diary: what was built, why, and every real bug hit along the way.

---

## Milestone 1 — Architecture & Project Scaffolding
FastAPI app factory, typed Pydantic config, structured JSON logging, multi-stage
Dockerfile, docker-compose with Postgres+Redis. Key bugs: config `.env` path
resolution depended on invocation directory (fixed by anchoring to `__file__`);
Docker port collisions with other running containers (fixed via configurable
host ports); a stale local file caused a "fix" to silently not apply (lesson:
verify a fix landed on disk before assuming a retry will behave differently).

## Milestone 2 — Database Design
6 models + 2 association tables (User, Job, Resume, Application, Score, Skill).
UUID primary keys, Single Table Inheritance for User roles, Application/Score
as first-class entities (not bare join tables), normalized Skill table instead
of JSON arrays. Built a portable `GUID` type and `JSON().with_variant(JSONB())`
so unit tests run against fast SQLite while production uses real Postgres
types. Key bugs: Windows/WSL2 port mismatch running Alembic outside Docker
(fixed by always running Alembic inside the container); bind-mount permission
denial writing migration files (`chmod -R a+rwX`); Alembic's autogenerate
doesn't emit import statements for custom types (fixed permanently via the
`script.py.mako` template).

## Milestone 3 — Authentication & RBAC
bcrypt password hashing, stateless JWT tokens, `get_current_user` +
`require_role()` dependency-based RBAC, framework-agnostic service layer.
Never reveals whether "email not found" vs "wrong password" (user enumeration
defense). Key bug: FastAPI's `TestClient` dispatches requests to a worker
thread; SQLAlchemy's default SQLite pooling hands out a different connection
per thread, so the connection that created tables and the connection the
endpoint queried were different, isolated in-memory databases. Fixed with
`poolclass=StaticPool`.

## Milestone 4 — Resume Upload & Parsing Pipeline
`StorageBackend` ABC + local implementation (S3-swappable later),
`pdfplumber`/`python-docx` extraction, text cleaning. Parsing failures degrade
gracefully (resume still saved, `parsed_text=None`) rather than failing the
upload. Key bugs: a lost Alembic migration file after a `git reset --hard`
recovery (root cause: revision file never committed) — restored via a
hand-written no-op placeholder migration matching the DB's recorded revision;
GitHub blocking PAT pushes to `.github/workflows/` without the `workflow`
scope (resolved by removing the unused placeholder rather than widening token
permissions).

## Milestone 5 — NER, Skill & Experience Extraction
182 curated skills (sourced from Microsoft's open-source
`SkillsExtractorCognitiveSearch` dataset, properly attributed), spaCy
`PhraseMatcher` gazetteer matching (blank pipeline — no full model download
needed for phrase matching), regex-based experience extraction, keyword-based
education level extraction. Idempotent seed script kept separate from
migrations. Key bug: Postgres auto-creates enum types as a side effect of
`CREATE TABLE` but NOT `ALTER TABLE ADD COLUMN` — Alembic's autogenerate
emitted `add_column` for a new enum without the corresponding `CREATE TYPE`,
producing `UndefinedObject: type "education_level" does not exist`. Fixed by
explicitly calling `sa.Enum(...).create(op.get_bind(), checkfirst=True)`
before the column is added, and added a permanent reminder to the migration
template.

---

## Milestone 6 — Embeddings & FAISS Semantic Search

**Goal:** Compare resumes and job descriptions by semantic meaning, not
just keyword overlap — recruiters submit a job description and get back
the most relevant resumes ranked by similarity.

**What we built:**
- `app/ai/embeddings.py` — `all-MiniLM-L6-v2` sentence embeddings, cached model instance
- `app/ai/faiss_index.py` — `IndexFlatIP` similarity search over resume vectors
- `app/services/search_service.py` — orchestrates embedding + index + ranking
- `app/api/v1/endpoints/search.py` — `POST /search/resumes`, recruiter-only
- `Resume.embedding` column (portable JSON, same pattern as `Score.explanation`)
- Wired into `resume_service.upload_resume` — embedding computed once at upload time
- Dockerfile pre-caches the model at build time (no runtime/test-time download)
- Tests: embedding quality (similar text scores higher than dissimilar text,
  against the real model — not mocked), FAISS index math in isolation
  (synthetic vectors), and a full end-to-end search test (upload two very
  different resumes, confirm the relevant one ranks first)

**Key decisions:**
- **`all-MiniLM-L6-v2` over larger models** — 384 dimensions, ~5x faster
  inference, modest quality trade-off that's acceptable for broad thematic
  resume-to-job matching (vs. nuanced literary similarity).
- **FAISS index rebuilt in-memory per search, not persisted/incremental** —
  index construction is near-instant even at thousands of vectors, and
  rebuilding from the DB's current state makes index/database drift
  structurally impossible. The genuinely expensive part (model inference)
  already happened once at upload time; this only does cheap vector math.
  Explicitly stated limitation: this would need to change (persisted,
  incrementally-updated index) at a much larger scale.
- **`IndexFlatIP` (inner product), not `IndexFlatL2`** — embeddings are
  L2-normalized at generation time, so inner product IS cosine similarity;
  avoids a separate normalization step at search time.
- **Embeddings stored as portable JSON, not pgvector** — avoids requiring
  the pgvector Postgres extension for a portfolio project; FAISS (in-memory)
  handles the actual similarity math, so Postgres only needs to durably store
  the raw vector.
- **Search scoped across ALL candidates, unlike resume upload/fetch** —
  a deliberate, stated exception to the "scope to owner" pattern from
  Milestone 4: a recruiter searching for candidates needs visibility across
  the whole pool; that's the point of the feature, not an access-control gap.
- **Model pre-cached in the Docker image at build time** — without this, the
  first API call or test run after a fresh deploy silently triggers an ~80MB
  network download, adding unpredictable latency and a hidden network
  dependency to CI.
- **Decoupled from `Job` CRUD (which doesn't exist yet)** — accepts raw job
  description text rather than requiring a `Job` row, so the feature is fully
  usable now and will plug into real job postings in Milestone 7 with no
  changes to the search logic itself.

**Bugs hit & root causes:** *(pending your test run against the real environment)*

**Status:** Pending your `docker compose build` + migration + `pytest -m unit` run.

---

## Milestone 7 — Explainable Scoring Engine

*(upcoming)*
