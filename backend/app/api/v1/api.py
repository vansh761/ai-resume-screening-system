"""Versioned API router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import analysis, applications, auth, jobs, resumes, search, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(resumes.router)
api_router.include_router(search.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(analysis.router)
