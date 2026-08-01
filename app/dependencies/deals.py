from __future__ import annotations

from fastapi import Depends

from app.core.exceptions import Forbidden
from app.dependencies.auth import get_current_user
from app.models.user import User, UserRole
from app.permissions.roles import DEALS_VIEW, has_permission


async def require_deal_view(current_user: User = Depends(get_current_user)) -> User:
    """Allow staff with the view permission and clients (scoped to their own deals)."""
    if current_user.role != UserRole.CLIENT and not has_permission(current_user, DEALS_VIEW):
        raise Forbidden("Insufficient permissions")
    return current_user
