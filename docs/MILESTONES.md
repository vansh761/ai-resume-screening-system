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

## Milestone 7 — Job CRUD & Explainable Scoring Engine

**Goal:** Recruiters post jobs, candidates apply with a resume, and every application gets a score a recruiter can audit factor by factor.

**What we built:**
- `Job` gained `min_education_level` and `embedding`; endpoints to create, list, fetch and open/close jobs (recruiters see their own jobs; candidates see only OPEN ones)
- `POST /applications/` creates an application and scores it immediately; `GET /applications/for-job/{id}` returns applicants ranked best-fit first
- `app/ai/scoring.py`: eight factors combined with fixed, published weights (skills 0.30, semantic similarity 0.20, experience 0.15, education 0.10, ATS 0.10, resume quality 0.10, certifications 0.025, projects 0.025). Each factor's inputs and the weights themselves are stored in `Score.explanation`

**Key decisions:**
- Honest about factor quality: skills, experience, education and semantic similarity use extracted or computed data; ATS and quality are structural heuristics; certifications and projects are keyword counts with deliberately low weight
- Missing data earns nothing: a job requiring 3 years of experience scores 0 on that factor when none could be extracted (not 100); a job with no requirement scores 100
- Required skills count 70%, preferred skills 30%
- Scoring runs synchronously at apply time (Milestone 10 later added a guard so only fully processed resumes can be scored)
- Someone else's resume or a draft job returns 404, not 403, so existence isn't revealed

**Bugs hit & root causes:**
- The Milestone 7 files had not actually been copied into the project, so the first migration was generated against the old `Job` model and lacked both new columns. Caught by reading the migration before applying it and by running `cat` on the model inside the container. Lesson: verify what the container sees, not what you think you copied.
- The no-op placeholder migration from the Milestone 4/5 recovery worked on the old database but could not survive a fresh one (it would have skipped creating every table). Found by setting the project up from scratch; replaced with one clean baseline migration.
- The Docker build pulled the CUDA build of PyTorch (gigabytes) and timed out. Fixed by installing the CPU-only wheel first.

**Status:** Done, 88 tests passing.

---

## Milestone 8 — Clustering, Duplicate Detection & Similar Candidates

**Goal:** Reuse the stored embeddings to answer three recruiter questions: what groups exist among my applicants, which resumes are duplicates, and who else looks like this candidate.

**What we built:**
- `GET /analysis/jobs/{id}/clusters`: k-means over a job's applicants, labelled by each cluster's three most common skills
- `GET /analysis/duplicates`: pairwise cosine similarity at or above 0.97
- `GET /analysis/resumes/{id}/similar`: FAISS search using the resume's own embedding as the query, excluding itself

**Key decisions:**
- Cluster count is a simple heuristic (one per ~3 applicants, capped at 6) rather than the elbow method or silhouette analysis; at dozens of applicants per job those add complexity without real benefit
- Duplicate detection is O(n²). That is fine for hundreds of resumes and wrong for millions, where locality-sensitive hashing or an approximate nearest-neighbour index would replace it. The 0.97 threshold is high on purpose so two similar backend engineers aren't flagged
- Clusters are scoped to one job's applicants because that is the decision a recruiter actually makes
- Recruiters can query any resume's neighbours (system-wide visibility is the point of these tools), unlike the candidate-scoped resume endpoints

**Bugs hit & root causes:** None worth recording; 102 tests passed on the first run.

**Status:** Done.

---

## Milestone 9 — LLM Insights (Gemini)

**Goal:** Recruiter-facing interview questions and candidate-facing summaries and resume improvement suggestions.

**What we built:**
- `app/ai/llm_client.py`: Gemini via the `google-genai` SDK in JSON mode, one error type (`LLMGenerationError`) for every failure, retry with exponential backoff for 503/429 only
- `app/ai/resume_insights.py`: prompts with fixed output shapes for summary, interview questions (tailored to the resume-job pair) and improvement suggestions
- `GET /insights/resumes/{id}/summary` and `/improvements` (candidate-scoped), `GET /insights/applications/{id}/interview-questions` (scoped to the job's recruiter); 503 when the LLM is unavailable
- Results cached in `Resume.ai_summary`, `Resume.improvement_suggestions` and `Application.interview_questions`

**Key decisions:**
- Hosted free-tier API rather than a small local model: paid APIs were ruled out on cost, and small local models are weak at open-ended generation and add another heavy dependency
- Lazy generation plus caching: at the time of the build the free tier allowed roughly 10 requests per minute and 250 per day, so the LLM is called at most once per item
- `google-genai`, not `google-generativeai` (sunset in November 2025)
- The real-API test sits behind its own pytest marker so it never runs by default or spends quota

**Bugs hit & root causes:**
- Model names are moving targets: `gemini-2.5-flash` returned 404 for new users, `gemini-3.8-flash` returned 503 from heavy demand, and `gemini-3.5-flash-lite` worked. The real-API test caught each one. The model name lives in config, not code
- The 503s motivated the retry logic; it only retries transient errors because retrying a bad key just delays the same failure
- `.env` had been tracked by git since Milestone 1, before `.gitignore` existed. `git log` showed it was only ever committed with placeholder values, never the Gemini key, and it was untracked before the first commit that could have included the key
- Two tests failed because they committed a `Resume` without an owner (NOT NULL constraint). Tests that only build objects in memory never hit database constraints; tests that commit do

**Status:** Done, 109 tests plus the real-API test passing.

---

## Milestone 10 — Background Processing (Celery)

**Goal:** Stop making the person uploading a resume wait for text extraction, NLP and embedding.

**What we built:**
- `POST /resumes/upload` now validates and stores the file, creates the `Resume` as PENDING, commits, then enqueues a Celery task. Clients poll `GET /resumes/{id}` until the status is `completed` or `failed`
- `Resume.processing_status` (PENDING / COMPLETED / FAILED), stored as VARCHAR with `native_enum=False` so the migration avoids the Postgres ALTER TABLE enum problem from Milestone 5. A COMPLETED server default backfills older rows truthfully, since they were processed synchronously
- `app/services/resume_processing_service.py`: the pipeline as a plain function taking a Session, with no Celery in it. `app/workers/tasks.py` is a thin wrapper around it
- `app/workers/celery_app.py`: Redis broker, JSON-only serialization, `acks_late`, `reject_on_worker_lost`, prefetch 1
- 409 guards: applying with, or requesting AI insights for, a resume that is not COMPLETED, so a half-processed resume can never receive a permanent near-zero score or burn LLM quota
- A `worker` service in docker-compose that reuses the API image, plus `scripts/requeue_stale_pending.py` to recover stuck resumes
- 13 new tests (122 total)

**Key decisions:**
- Commit before enqueue, so the worker can see the row
- The pipeline is idempotent because `acks_late` means at-least-once delivery: it skips COMPLETED resumes and clears old `ResumeSkill` rows before re-adding them
- Permanent failures (unreadable file) mark the resume FAILED and do not retry; transient database errors retry with backoff and jitter
- Tests replace `dispatch_resume_processing` with an inline runner instead of using `task_always_eager`: the real task opens its own Postgres session, while tests use an in-memory SQLite session
- 201, not 202, because the Resume resource exists immediately
- LLM insights stay synchronous: they are explicit, on-demand requests where a few seconds is acceptable
- Local file storage works across the API and worker only because both mount `./backend`; production would swap in an S3 backend behind the `StorageBackend` interface

**Measured on a 2-core, 2.8 GB machine:** upload returns in 0.05-0.9s; warm processing takes 2-3s; the first task after a worker restart takes about 28s, of which 23.6s is loading the embedding model; a corrupt file reaches FAILED in under a second; a task enqueued while no worker was running (queue length 1) was processed after the worker started.

**Bugs hit & root causes:**
- All 122 tests passed but the live upload returned 500: `PermissionError: 'uploads'`. The container user cannot create a directory inside the bind mount, and the tests redirect storage to a temp directory, so no test ever touched the real filesystem. Fixed by creating the directory with the right permissions
- uvicorn `--reload` was watching all of `/app`, including a leftover 45,092-file virtualenv on a WSL bind mount. Idle API CPU was about 82%, requests timed out and cold starts took minutes. Deleting the virtualenv and using `--reload-dir app` dropped idle CPU to 1.3%, and the first task fell from 116-194s to 28s
- The same stray virtualenv made the Docker build context 459 MB (17 minutes to transfer) and `COPY . .` had been copying `backend/.env` into the image. Added `backend/.dockerignore`
- Giving the worker its own `build:` block triggered a rebuild that failed on DNS inside WSL. Fixed by reusing the API image with `pull_policy: never`
- `docker compose exec` rejects heredocs unless you pass `-T`; and scripts run as `python scripts/x.py` put `scripts/` on the import path, not `/app`
- One task that a worker had received was never completed and left a resume PENDING for days. The cause was not established; the requeue script recovered it

**Known gaps (deliberate):**
- Stale-PENDING recovery is a manual script. A Celery Beat sweeper or a transactional outbox is the production answer, and this is also the window between the commit and the enqueue if the API dies there
- `concurrency=1`, and each worker process loads its own copy of the model
- No task monitoring such as Flower
- `DEBUG=true` echoes every SQL statement into the API and worker logs

**Status:** Done. 122 tests passing, and the async path verified end to end against real Redis, Postgres and a worker.
