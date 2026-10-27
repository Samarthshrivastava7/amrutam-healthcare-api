from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.routes.auth import get_current_user
from app.db.session import get_db
from app.models.user import User, UserRole


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required",
        )
    return current_user
