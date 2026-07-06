"""
Authentication endpoints.

This router contains NO business logic — every rule lives in
`app.services.auth_service`. The router's only job is: parse the
request, call the service, translate domain exceptions into HTTP
responses, return a schema. This thin-controller pattern is what keeps
`auth_service` testable without FastAPI and keeps this file readable
even as more endpoints are added.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.db.session import get_db
from app.schemas.user import Token, UserCreate, UserLogin
from app.services.auth_service import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    authenticate_user,
    create_user,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate, db: Session = Depends(get_db)) -> Token:
    """
    Registers a new user (recruiter or candidate) and returns an access
    token immediately — so the client doesn't need a separate login
    call right after signing up.
    """
    try:
        user = create_user(db, user_in)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    access_token = create_access_token(subject=str(user.id), extra_claims={"role": user.role.value})
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    """Authenticates an existing user and returns a fresh access token."""
    try:
        user = authenticate_user(db, credentials.email, credentials.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    access_token = create_access_token(subject=str(user.id), extra_claims={"role": user.role.value})
    return Token(access_token=access_token)
