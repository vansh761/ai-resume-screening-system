"""
Pydantic schemas for authentication and user data.

Design decision
----------------
These are deliberately separate classes from the SQLAlchemy `User`
model in `app/models/user.py`, even though the fields overlap heavily.
This is the standard FastAPI pattern for a reason: the ORM model
represents what's stored in the database (including `hashed_password`),
while these schemas represent what crosses the API boundary. `UserRead`
below has NO password field at all — it is structurally impossible to
accidentally leak a password hash in an API response, because the
response model doesn't have a slot for it.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Request body for POST /auth/signup."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    role: UserRole


class UserLogin(BaseModel):
    """Request body for POST /auth/login."""

    email: EmailStr
    password: str


class UserRead(BaseModel):
    """
    Public-facing user representation. No password field exists here —
    by construction, not by convention — so it can never leak.
    """

    model_config = ConfigDict(from_attributes=True)  # Allows building this from an ORM object directly.

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    """Response body for successful signup/login."""

    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """The decoded claims we expect inside a valid JWT."""

    sub: str  # user ID as a string
    role: UserRole
    exp: int
