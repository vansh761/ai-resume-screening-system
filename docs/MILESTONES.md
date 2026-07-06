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

**Status:** ✅ Done — pending your `pytest -m unit` run to confirm on your machine.

---

## Milestone 4 — Resume Parsing Pipeline

*(in progress — entry will be filled in as this milestone completes)*
