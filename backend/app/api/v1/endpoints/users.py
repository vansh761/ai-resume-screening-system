"""User endpoints."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/recruiter-only-example", response_model=UserRead)
def recruiter_only_example(
    current_user: User = Depends(require_role(UserRole.RECRUITER)),
) -> User:
    return current_user
