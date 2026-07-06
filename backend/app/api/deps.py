"""
Reusable FastAPI dependencies: DB session, current user extraction, and
role-based access control.

Design decision
----------------
`require_role` is a dependency FACTORY (a function that returns a
dependency), not a single fixed dependency. This lets each endpoint
declare exactly which role(s) it needs:

    @router.post("/jobs", dependencies=[Depends(require_role(UserRole.RECRUITER))])

The access requirement is visible in the route signature itself —
a reviewer (or you, in an interview) can answer "who can call this
endpoint" by reading one line, without tracing through the function body.
"""

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

# `tokenUrl` here only affects the auto-generated Swagger UI's "Authorize"
# button — it doesn't perform any actual redirect or validation itself.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{'/api/v1'}/auth/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """
    Decodes the bearer token from the Authorization header and loads
    the corresponding user from the database.

    We re-fetch the user from the DB on every request (rather than
    trusting the token's embedded claims alone) so that, e.g., an
    admin deactivating a user (`is_active = False`) takes effect
    immediately — not just after the user's existing token expires.
    """
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise CREDENTIALS_EXCEPTION

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_EXCEPTION

    return user


def require_role(*allowed_roles: UserRole) -> Callable[[User], User]:
    """
    Returns a dependency that enforces the current user has one of the
    given roles. Usage:

        Depends(require_role(UserRole.RECRUITER))
        Depends(require_role(UserRole.RECRUITER, UserRole.CANDIDATE))  # either role
    """

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: "
                f"{', '.join(r.value for r in allowed_roles)}",
            )
        return current_user

    return role_checker
