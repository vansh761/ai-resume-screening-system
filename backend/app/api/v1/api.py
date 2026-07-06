"""
Versioned API router aggregation.

Every new endpoint module gets registered here, once. `main.py` only
ever imports this single `api_router` — it never knows about individual
endpoint files. This is what makes API versioning painless: a future
`v2` package can exist side-by-side with different routers included
into its own `api_router`, with zero changes to `main.py`.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
