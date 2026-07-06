"""
Security primitives: password hashing and JWT token handling.

This module intentionally contains NO business logic (no "who is allowed
to do what") — that lives in `app/api/deps.py` and the service layer.
This file only answers two narrow questions: "does this password match
this hash" and "is this token valid, and who does it belong to."
Keeping these concerns separate means the cryptographic primitives can
be unit-tested in complete isolation from FastAPI or the database.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# `bcrypt` is deliberately slow (tunable via its "rounds" parameter) —
# this is a defense against brute-force attacks, not a performance bug.
# CryptContext also handles hash-scheme migration for free: if we ever
# move to a stronger algorithm later, passlib can verify old bcrypt
# hashes while issuing new ones with the updated scheme.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Hashes a plaintext password for storage.

    The plaintext password must NEVER be logged, stored, or transmitted
    anywhere beyond this function call — this is the only place in the
    codebase that should ever see it in plain form.
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Checks a plaintext password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """
    Issues a signed JWT access token.

    `subject` is the user's ID (as a string — JWT `sub` claims are
    conventionally strings, not UUID objects). `extra_claims` lets us
    embed the user's role directly in the token, so role checks
    (`require_role`) don't need a database round-trip on every request —
    the role travels with the token itself.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode: dict[str, Any] = {"sub": subject, "exp": expire}
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Verifies and decodes a JWT.

    Returns None (rather than raising) on any failure — expired,
    malformed, or signed with a different key. The caller (a FastAPI
    dependency) turns that None into a proper 401 response; this
    function's job is only to answer "is this token trustworthy," not
    to know about HTTP status codes.
    """
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
