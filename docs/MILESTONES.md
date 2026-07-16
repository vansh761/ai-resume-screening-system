# Project Milestones Log

This file is the actual build diary — what was built, why each decision was
made, and every real bug hit along the way (with root cause, not just the
fix). Treat this as interview prep material: if you can explain any entry
below in your own words, you can defend that part of the project.

Each entry follows the same shape: **Goal → What we built → Key decisions →
Bugs hit & root causes → Status**.

---

## Milestone 1 — Architecture & Project Scaffolding

**Goal:** Stand up the skeleton of the system — folder structure, config,
logging, containerized dev environment — before any feature code exists.

**What we built:**
- Layered folder structure: `api/ schemas/ services/ models/ ai/ workers/ core/ db/`
- `app/core/config.py` — typed config via Pydantic `BaseSettings`, fail-fast on missing env vars
- `app/core/logging_config.py` — structured JSON logging (human-readable in dev, JSON in prod)
- `app/main.py` — FastAPI app factory, global exception handler, `/health` endpoint
- `docker-compose.yml` + multi-stage `Dockerfile` (non-root container user, healthchecks)
- `pytest.ini` + first smoke test

**Key decisions:**
- Application factory pattern (`create_application()`) instead of a bare module-level `app = FastAPI()` — makes the app trivially testable with fresh instances per test.
- Config centralized in one Pydantic model rather than scattered `os.environ.get()` calls — single source of truth, type-safe, fails at startup instead of mid-request.
- Structured JSON logs instead of `print()` — machine-parseable for future log aggregation (ELK/Datadog).

**Bugs hit & root causes:**
1. **Config path resolution bug.** `env_file=".env"` in `SettingsConfigDict` resolves relative to the *current working directory*, not the project root. Running `pytest` from `backend/` looked for `backend/.env`, found nothing, and `SECRET_KEY`/`POSTGRES_PASSWORD` validation failed. **Fix:** anchor the `.env` path to an absolute path derived from `__file__`, so config loading is deterministic regardless of invocation directory.
2. **Docker Desktop not running.** The `docker compose up` pipe error (`dockerDesktopLinuxEngine`) simply meant the Docker daemon wasn't started. Resolved by using WSL2's native Docker engine directly instead of Docker Desktop (lighter weight, avoided the laptop-hanging issue entirely).
3. **Port collision.** A pre-existing container (`smarthome-ai-backend`) already held host port 8000, and Postgres/Redis's default ports could collide too. **Fix:** made all host-side ports configurable via env vars with sane fallbacks (`BACKEND_PORT:-8010`, `POSTGRES_HOST_PORT:-5433`, `REDIS_HOST_PORT:-6380`) instead of hardcoding — a real production habit, not just a workaround.
4. **A "fix" that didn't apply.** A `docker-compose.yml` port edit was written but the copy in WSL2 was stale (predated the fix, confirmed via file timestamp) — the actual lesson: verify a fix landed on disk (`cat`, `grep`, timestamps) before assuming a retry will behave differently.

**Status:** ✅ Done — `docker compose up --build` runs clean, `curl /health` returns `200`, `pytest` passes.

---

## Milestone 2 — Database Design

**Goal:** Design and implement the persistent schema — users, jobs,
resumes, applications, scores, skills — plus Alembic migrations to
version-control schema changes.

**What we built:**
- `app/db/base_class.py` — declarative `Base`, `TimestampMixin`, naming convention for constraints, and a custom portable `GUID` type
- `app/db/session.py` — connection pool + `get_db()` FastAPI dependency
- 6 models + 2 association tables: `User`, `Job`, `Resume`, `Application`, `Score`, `Skill`, `ResumeSkill`, `JobSkill`
- Alembic wired to read the DB URL from `app.core.config.settings` (no URL duplicated in `alembic.ini`)
- Unit tests (SQLite, fast) + an integration test tier (real Postgres, exercises JSONB)

**Key decisions:**
- **UUID primary keys**, generated client-side, instead of auto-increment integers — avoids leaking row counts/growth rate through the API, and IDs are known before INSERT commits (matters once Celery workers reference records asynchronously, from Milestone 10 onward).
- **Single Table Inheritance for `User`** (one table, `role` enum) instead of separate `Recruiter`/`Candidate` tables — deliberately the simpler option now; a clean, isolated migration path exists later if role-specific attributes grow.
- **`Application` as its own entity**, not a bare join table — because "candidate applied to job with resume X" carries its own status/lifecycle, which a plain many-to-many table can't hold.
- **`Score` separated from `Application`** — scores are a recomputable, derived artifact; separating them from stable workflow state means re-running the scoring algorithm later never touches application history.
- **Normalized `Skill` table + association tables**, not a JSON array of skill strings — makes "missing skills detection" (Milestone 7) a clean set operation instead of fuzzy string matching, and makes skill filtering indexable.
- **Portable `GUID` type + `JSON().with_variant(JSONB(), "postgresql")`** — native UUID/JSONB in production Postgres, plain CHAR/JSON under SQLite for the unit test tier. The trade-off being made explicitly: fast unit tests (no DB dependency) vs. full-fidelity integration tests (real Postgres) — both tiers exist for a reason, see `pytest.ini` markers.

**Bugs hit & root causes:**
1. **`.env` port mismatch across Windows/WSL2 boundary.** Alembic run from a Windows Python venv tried `127.0.0.1:5432` (the container's *internal* port), while Docker Compose actually published Postgres on host port `5433` (per the Milestone 1 port-conflict fix). Root cause: two separate execution environments (Windows venv vs. WSL2 Docker) each needing the DB URL resolved differently. **Fix:** stopped running Alembic from Windows entirely; run it inside the container instead (`docker compose exec backend alembic ...`), where `POSTGRES_HOST=postgres`/`POSTGRES_PORT=5432` are already correct.
2. **Permission denied writing the migration file.** The container runs as non-root `appuser`, and `docker-compose.yml` bind-mounts the host folder over `/app` — so host filesystem permissions govern, not the `chown` baked into the image at build time. **Fix:** `chmod -R a+rwX backend/alembic` on the host so the bind-mounted directory is writable from inside the container regardless of which user owns it.
3. **`NameError: name 'app' is not defined` during `alembic upgrade`.** Alembic's autogenerate renders custom (non-built-in) SQLAlchemy types like our `GUID` using their full dotted path (`app.db.base_class.GUID()`) but — per Alembic's own documented behavior — does **not** emit the corresponding import statement. **Fix:** patched the existing migration file with `import app.db.base_class`, and permanently added that import to `alembic/script.py.mako` so every future autogenerated migration includes it automatically.

**Status:** ✅ Done — `alembic upgrade head` applied cleanly (`-> 37ce979121ae, create initial schema`), all 8 tables + constraints exist in Postgres.

---

## Milestone 3 — Authentication & RBAC

**Goal:** JWT-based authentication with password hashing, plus
role-based route protection distinguishing recruiters from candidates.

**What we built:**
- `app/core/security.py` — bcrypt password hashing, JWT creation/verification
- `app/schemas/user.py` — `UserCreate`, `UserLogin`, `UserRead` (no password field, ever), `Token`
- `app/services/auth_service.py` — framework-agnostic business logic (`create_user`, `authenticate_user`)
- `app/api/deps.py` — `get_current_user` and `require_role()` dependency factory
- `app/api/v1/endpoints/auth.py` — `/auth/signup`, `/auth/login`
- `app/api/v1/endpoints/users.py` — `/users/me` (any authenticated user), `/users/recruiter-only-example` (role-gated, demonstrates the pattern every future recruiter-only endpoint will reuse)
- `app/api/v1/api.py` — router aggregation, mounted in `main.py` under `/api/v1`
- Full test suite: password hashing properties, JWT tamper detection, and an end-to-end HTTP test hitting signup → login → protected route → role-gated route

**Key decisions:**
- **bcrypt via passlib**, not a fast general-purpose hash — slowness is the point, it raises the cost of brute-forcing.
- **JWT, stateless** — no server-side session store to scale across multiple backend instances; trade-off is tokens can't be instantly revoked before expiry, so we keep `ACCESS_TOKEN_EXPIRE_MINUTES` short.
- **`authenticate_user` never reveals *which* part of the credentials was wrong** — same error for "no such email" and "wrong password," to prevent user-enumeration.
- **`get_current_user` re-fetches the user from the DB every request** instead of trusting the token's embedded claims alone — so deactivating a user takes effect immediately, not just after their token naturally expires.
- **`require_role()` as a dependency factory**, not an in-body `if` check — the access requirement is visible in the route signature itself.
- **Service layer has zero FastAPI imports** — `auth_service.py` only knows SQLAlchemy and domain models, so it's testable (and reusable from a future CLI/admin tool) without spinning up the whole app.
- **Tests exercise real HTTP requests** (FastAPI `TestClient` + `dependency_overrides` swapping Postgres for in-memory SQLite) rather than only unit-testing service functions in isolation — this is what actually proves the DI wiring and router work together, not just each piece alone.

**Bugs hit & root causes:**
- (Self-caught during review, before it reached you) An `str_replace` edit to `main.py`'s lifespan function accidentally deleted the `yield` statement — would have broken the FastAPI startup/shutdown lifecycle silently. Caught by re-viewing the file immediately after the edit rather than assuming it landed correctly — worth internalizing as a habit: always re-read a file after a mechanical edit, don't trust it blindly.
- Proactively pinned `bcrypt==4.0.1` alongside `passlib==1.7.4` — newer `bcrypt` (4.1+) removed the `__about__.__version__` attribute that older `passlib` versions probe for, a widely-reported real-world incompatibility that would otherwise surface as a confusing warning or crash on first `pip install`.
- **`sqlite3.OperationalError: no such table: users` in the end-to-end auth tests, despite `Base.metadata.create_all()` running successfully.** Root cause: FastAPI's `TestClient` dispatches each request to a worker thread (`anyio.to_thread.run_sync`), and SQLAlchemy's default SQLite pooling hands out a *different connection per thread*. The connection that created the tables (test's main thread) and the connection the endpoint queried against (worker thread) were two separate, isolated `:memory:` databases sharing only a URL string. Fixed by forcing `poolclass=StaticPool` so every thread reuses the exact same connection — the standard, documented pattern for testing FastAPI + SQLAlchemy + SQLite together. Notably, the plain model unit tests (no TestClient/HTTP layer involved, single-threaded) never hit this, which is exactly why it only surfaced in the end-to-end auth flow tests.
- Missing `email-validator` package (a soft dependency Pydantic needs specifically for the `EmailStr` type) surfaced only inside the Docker container after a `requirements.txt` change — root cause was simply forgetting to `docker compose build` after editing dependencies, since Docker caches the `pip install` layer and won't rerun it just because the requirements file on the host changed.

**Status:** ✅ Done — pending your `pytest -m unit` run to confirm on your machine.

---

## Milestone 4 — Resume Upload & Parsing Pipeline

**Goal:** Let candidates upload a PDF/DOCX resume, store it, and
extract clean plain text from it — the first stage of the AI pipeline.

**What we built:**
- `app/services/storage/` — a `StorageBackend` ABC + `LocalStorageBackend`, swappable for S3 later with zero changes to calling code
- `app/ai/text_extraction.py` — `pdfplumber` for PDFs, `python-docx` for DOCX
- `app/ai/text_cleaning.py` — Unicode normalization, whitespace/blank-line collapsing
- `app/services/resume_service.py` — orchestrates validation → storage → extraction → DB persistence
- `app/api/v1/endpoints/resumes.py` — `POST /resumes/upload`, `GET /resumes/`, `GET /resumes/{id}`, all candidate-scoped
- Tests: storage backend (including a path-traversal rejection test), text cleaning, extraction against real generated PDF/DOCX files (not mocks), and a full HTTP-level upload flow

**Key decisions:**
- **`pdfplumber` over `pypdf`** — resumes are visually structured (columns, indented bullets), and `pdfplumber` preserves reading order far better; the trade-off (slower) is acceptable since parsing isn't on a hot path and will move to a Celery worker in Milestone 10 anyway.
- **Storage abstraction (ABC + local implementation)** built now, even though only local disk is implemented — the same Dependency Inversion pattern as the DB layer, so an S3 backend later is an additive change, not a rewrite.
- **Extension allow-list, not a deny-list**, for upload validation — fails safe: anything not explicitly permitted is rejected, rather than trying to enumerate every dangerous extension.
- **Parsing failures degrade gracefully, not fatally** — if `pdfplumber`/`python-docx` can't extract text (corrupted file, scanned image with no text layer), the resume record is still created with `parsed_text = None` and the failure is logged, rather than rejecting the whole upload. The file was still saved successfully; that shouldn't be thrown away because parsing had trouble.
- **404, not 403, for another candidate's resume** — same user-enumeration reasoning as the Milestone 3 login error message: don't reveal that a given resume ID exists at all to someone who doesn't own it.
- **Tests use real generated PDF/DOCX bytes** (via `fpdf2` and `python-docx` itself), not mocked parser calls — a mock only proves the code calls the mock correctly, never that extraction actually works against a real file.

**Bugs hit & root causes:**
- **Tangled `git pull --rebase` conflict.** A prior push attempt (before the StaticPool fix existed) had put an earlier, incomplete version of `conftest.py` on GitHub via a separate session. Rebasing tried to replay multiple divergent local commits on top of that, produced cascading conflicts across unrelated `__pycache__` files (further proof `.gitignore` needed to land earlier — a file that should never have been tracked can't cleanly "conflict," it just keeps causing noise), and one intermediate commit even got force-continued with unresolved `<<<<<<<`/`>>>>>>>` conflict markers still literally inside `app/db/session.py` — which then surfaced as a Python `SyntaxError: invalid decimal literal` at test-collection time (git's conflict markers are not valid Python). **Fix:** rather than resolving conflict-by-conflict through an increasingly confused rebase, aborted entirely (`git rebase --abort`), hard-reset local `main` to match `origin/main` exactly (`git reset --hard origin/main` — safe specifically because it never touches *untracked* files, and all of Milestone 4's new files were still untracked at that point), then cleanly reapplied the one fix that actually mattered (the `conftest.py` StaticPool change) on top of a known-good base. **General lesson:** when a rebase spirals into conflicts across files that shouldn't be tracked at all, untangling each conflict is usually the wrong instinct — resetting to a known-good remote state and cleanly reapplying just the real change is faster and safer.

**Status:** ✅ Done — `38 passed, 1 deselected`.

---

## Milestone 5 — NER, Skill & Experience Extraction

**Goal:** Turn clean resume text into structured data: a list of
skills, total years of experience, and highest education level.

**What we built:**
- `app/data/skill_seed_data.py` — 182 curated skills, sourced from Microsoft's open-source `SkillsExtractorCognitiveSearch` dataset (properly attributed; see file docstring for provenance and the trade-off of curating a subset vs. the full ~2,100-entry file)
- `app/db/seed.py` — idempotent seeding script (`python -m app.db.seed`)
- `app/ai/skill_extraction.py` — spaCy `PhraseMatcher` gazetteer matching against the `Skill` table
- `app/ai/experience_extraction.py` — regex-based years-of-experience detection
- `app/ai/education_extraction.py` — keyword-based education level detection, added `EducationLevel` enum + two new `Resume` columns
- Wired into `resume_service.upload_resume` — runs automatically after text extraction succeeds
- `ResumeRead` schema extended with `extracted_skills`, `years_experience`, `education_level`
- Tests: extraction logic unit-tested in isolation, plus one true end-to-end test (seed a skill → upload a resume mentioning it → confirm it's in the API response)

**Key decisions:**
- **Gazetteer/dictionary matching over spaCy's statistical NER** — precise, explainable (every match traces to an exact known skill), and fast. Trade-off stated plainly: only finds skills already in the vocabulary; a brand-new framework won't be detected until seeded. Chosen deliberately over the alternative of a model that "guesses," which would trade explainability for marginal recall.
- **`spacy.blank("en")` instead of downloading `en_core_web_sm`** — phrase matching only needs tokenization, not the full statistical pipeline; skips an unnecessary model download, keeping the Docker build lighter and faster.
- **Regex over models for experience/education** — both are expressed in a small, conventional vocabulary on resumes; a well-tested regex is more predictable and auditable than model inference for this kind of deterministic pattern.
- **Seed data sourced externally, not hand-invented** — 182 entries curated from a real, cited open-source dataset (Microsoft's `SkillsExtractorCognitiveSearch`) rather than a list I made up, with the provenance and the curation trade-off documented directly in the seed file's docstring.
- **Seeding kept separate from Alembic migrations** — migrations describe schema shape; a standalone idempotent script handles reference data, so re-running it (new dev machine, CI, fresh clone) is always safe.
- **Nullable extraction fields, not defaulted to 0/empty** — a resume where extraction hasn't run yet must be distinguishable from one where extraction ran and found nothing.

**Bugs hit & root causes:** *(will be filled in as they occur against your real environment)*

**Status:** 🚧 Pending your `docker compose build` + `pytest -m unit` run, plus running the seed script, to confirm.

---

## Milestone 6 — Embeddings & FAISS Semantic Search

*(in progress — entry will be filled in as this milestone completes)*
