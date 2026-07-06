"""
User endpoints — demonstrates the two access-control patterns every
future router in this project will reuse: "any authenticated user" and
"specific role only."
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Returns the profile of whichever user's token was sent — recruiter
    or candidate, no role restriction beyond "must be logged in."
    """
    return current_user


@router.get("/recruiter-only-example", response_model=UserRead)
def recruiter_only_example(
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> User:
    """
    Demonstrates role-gating: a candidate's valid token still gets a
    403 here, because `require_role` checks the role, not just whether
    the token is valid. Real recruiter-only endpoints (job creation,
    candidate scoring, etc.) will use this exact same dependency
    starting in Milestone 4+.
    """
    return current_user
