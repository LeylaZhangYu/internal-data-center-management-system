from typing import Iterable

from fastapi import Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.models import User


def require_roles(*roles: Iterable[str]):
    allowed = set(roles)

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return checker
