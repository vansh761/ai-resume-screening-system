"""
Application configuration module.

Design decision
----------------
We use Pydantic's `BaseSettings` instead of raw `os.environ.get(...)` calls
scattered across the codebase. This gives us three things a plain dict
lookup can't:

1. Fail-fast validation: if a required env var is missing or malformed,
   the application refuses to start (instead of crashing later, mid-request,
   in production).
2. A single source of truth: every module imports `settings` from here
   rather than re-reading the environment, which makes config auditable
   and testable (we can monkeypatch `settings` in tests).
3. Type safety: `DEBUG` is a real `bool`, `DATABASE_POOL_SIZE` is a real
   `int` — no stringly-typed config bugs.

This is the same pattern used in production FastAPI services at scale
(Netflix, Uber's Python services, etc.) and is FastAPI's own documented
recommendation for settings management.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve the project root's `.env` by an absolute path derived from this
# file's own location, NOT from the current working directory.
#
# Why this matters: `env_file=".env"` alone is resolved relative to
# wherever the process was launched from. That means `pytest` run from
# `backend/`, `uvicorn` run from the repo root, and Docker (where the
# working directory is `/app`) would all look in different places for
# the same file — and silently fail validation if the file isn't there.
# Anchoring to `__file__` makes config loading deterministic regardless
# of invocation directory.
#
# This file lives at: backend/app/core/config.py
# The project's .env lives at: <repo_root>/.env
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _PROJECT_ROOT / ".env"
_BACKEND_ENV_FILE = _PROJECT_ROOT / "backend" / ".env"


class Settings(BaseSettings):
    """
    Strongly-typed application settings, populated from environment
    variables (and a local `.env` file during development).

    Every field here is documented because in a production system,
    config IS documentation of what the service depends on.
    """

    model_config = SettingsConfigDict(
        # Accept either location: project-root `.env` (used by Docker Compose
        # for variable substitution) or `backend/.env` (convenient when
        # running `uvicorn`/`pytest` directly from inside `backend/`).
        # Pydantic reads files in order and lets later files override
        # earlier ones, so listing both is safe even if only one exists.
        env_file=(_ENV_FILE, _BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application metadata ---
    PROJECT_NAME: str = "AI Resume Screening System"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")  # development | staging | production
    DEBUG: bool = Field(default=False)

    # --- Security ---
    SECRET_KEY: str = Field(..., description="Used to sign JWTs. Must be set via env var.")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # --- CORS ---
    BACKEND_CORS_ORIGINS: List[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # --- Database ---
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = Field(..., description="Must be set via env var, never hardcoded.")
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "resume_screening"
    DATABASE_URL: PostgresDsn | None = None

    # --- Redis (caching + Celery broker) ---
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # --- Celery ---
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    # --- File uploads ---
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_RESUME_EXTENSIONS: List[str] = Field(default_factory=lambda: [".pdf", ".docx"])
    UPLOAD_DIR: str = "uploads"

    # --- Rate limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60

    # --- Pagination defaults ---
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str | None, info) -> str:
        """
        Build the Postgres DSN from individual components if not
        explicitly provided. Keeping components separate (host, user,
        password) rather than one big URL env var makes local dev
        overrides (e.g. changing just the port) trivial in docker-compose.
        """
        if isinstance(v, str) and v:
            return v
        data = info.data
        return (
            f"postgresql+psycopg://{data.get('POSTGRES_USER')}:"
            f"{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_HOST')}:"
            f"{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB')}"
        )

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker(cls, v: str | None, info) -> str:
        if isinstance(v, str) and v:
            return v
        data = info.data
        return f"redis://{data.get('REDIS_HOST')}:{data.get('REDIS_PORT')}/{data.get('REDIS_DB')}"

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_backend(cls, v: str | None, info) -> str:
        if isinstance(v, str) and v:
            return v
        data = info.data
        return f"redis://{data.get('REDIS_HOST')}:{data.get('REDIS_PORT')}/{data.get('REDIS_DB')}"


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.

    Why `lru_cache` instead of a plain module-level `settings = Settings()`:
    it lets us override settings cleanly in tests via
    `app.dependency_overrides[get_settings] = lambda: test_settings`,
    without needing to reload the whole module.
    """
    return Settings()


settings = get_settings()
