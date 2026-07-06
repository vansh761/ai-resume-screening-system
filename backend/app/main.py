"""
Application entrypoint.

This module wires together configuration, logging, middleware, and
routers. It deliberately contains NO business logic — its only job is
composition. Business logic lives in `app/services/`, endpoint routing
lives in `app/api/`. Keeping `main.py` thin is what allows the app to
grow to 50+ endpoints without this file becoming unmanageable.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manages startup/shutdown events.

    Why `lifespan` instead of the older `@app.on_event("startup")`:
    it's the FastAPI-recommended approach since it properly scopes
    resources (DB connection pools, ML model loading, etc.) and
    guarantees cleanup code runs even if startup raises partway through.
    """
    configure_logging()
    logger.info(f"Starting {settings.PROJECT_NAME} [{settings.ENVIRONMENT}]")

    # DB engine + connection pool are created at import time in
    # app/db/session.py (module-level `engine`). SQLAlchemy's pool is
    # lazy — the first real connection is only opened on first use, so
    # nothing extra is needed here for Milestone 2/3.
    # Milestone 6 will load the sentence-transformer model + FAISS index
    # here, once at startup, so it's not reloaded on every request.

    yield

    logger.info("Shutting down gracefully")


def create_application() -> FastAPI:
    """
    Application factory.

    Design decision
    ----------------
    We use a factory function rather than a bare module-level `app = FastAPI()`.
    This is what makes the app testable: `pytest` fixtures can call
    `create_application()` fresh for each test session with overridden
    settings, instead of importing a single global, already-configured
    instance that carries state between tests.
    """
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Global fallback error handler.

        Never leak raw stack traces to API clients in production — that's
        an information-disclosure risk. Log the full exception server-side,
        return a generic message client-side.
        """
        logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )

    @application.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """
        Liveness/readiness probe.

        Kubernetes, Docker Compose healthchecks, and load balancers all
        poll an endpoint like this to know whether to route traffic to
        this instance. It's one of the first things a production
        reviewer checks for.
        """
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_application()
