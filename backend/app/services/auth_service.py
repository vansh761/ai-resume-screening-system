"""
Authentication service layer.

Design decision
----------------
This module has zero FastAPI imports. It only knows about SQLAlchemy
sessions and our domain models. That's deliberate: business rules like
"an email must be unique" or "a login requires a matching password
hash" have nothing to do with HTTP — they're true whether triggered by
a REST endpoint, a CLI script, or a test. Keeping this layer
framework-agnostic is what makes it trivially unit-testable without
spinning up a FastAPI app at all, and what would let a future CLI
admin tool reuse this exact code.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    """Raised when signup is attempted with an email already in use."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials don't match any active user."""


def get_user_by_email(db: Session, email: str) -> User | None:
    """Looks up a user by email, or None if no such user exists."""
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def create_user(db: Session, user_in: UserCreate) -> User:
    """
    Creates a new user with a hashed password.

    Raises `EmailAlreadyRegisteredError` rather than letting a raw
    database IntegrityError bubble up — the API layer shouldn't need to
    know that "duplicate email" happens to be enforced via a unique
    constraint; it should just handle a domain-meaningful exception.
    """
    existing = get_user_by_email(db, user_in.email)
    if existing is not None:
        raise EmailAlreadyRegisteredError(f"Email already registered: {user_in.email}")

    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Verifies login credentials and returns the matching user.

    Raises `InvalidCredentialsError` for BOTH "no such user" and "wrong
    password" — never distinguish these in the response. Revealing
    "that email doesn't exist" vs "wrong password" tells an attacker
    which emails are registered, a classic user-enumeration leak.
    """
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Incorrect email or password")
    if not user.is_active:
        raise InvalidCredentialsError("Account is deactivated")
    return user
