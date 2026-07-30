from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import Unauthorized
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.services.auth import auth_service

security_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise Unauthorized("Invalid or expired access token")

    user_id = payload.get("sub")
    if not user_id:
        raise Unauthorized("Invalid token payload")

    return await auth_service.get_current_user(db, user_id)


class RoleChecker:
    def __init__(self, *allowed_roles: UserRole) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise Unauthorized("Insufficient permissions")
        return current_user
