import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import RoleChecker, require_permission
from app.models.user import User, UserRole
from app.permissions.roles import (
    USERS_VIEW,
    require_can_change_role,
    require_can_create_user,
    require_can_delete_user,
    require_can_manage_user,
    require_can_reset_password,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import (
    ResetPasswordResponse,
    UserCreate,
    UserCreateResponse,
    UserRead,
    UserRoleChangeRequest,
    UserShortRead,
    UserUpdate,
)
from app.services.user import user_service

router = APIRouter(prefix="/users", tags=["Users"])

admin_or_super = RoleChecker(UserRole.SUPER_ADMIN, UserRole.ADMIN)
manager_read = RoleChecker(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.MANAGER)


@router.get("/", response_model=PaginatedResponse[UserShortRead])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = Query(None, min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(USERS_VIEW)),
):
    users, total = await user_service.list_users(
        db, page=page, size=size, role=role, is_active=is_active, search=search
    )
    pages = (total + size - 1) // size
    return PaginatedResponse(
        items=users,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(USERS_VIEW)),
):
    return await user_service.get_user(db, user_id)


@router.post("/", response_model=UserCreateResponse, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    require_can_create_user(current_user, data.role)
    user, temporary_password = await user_service.create_user(db, data)
    return UserCreateResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        role=user.role,
        temporary_password=temporary_password,
    )


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    target = await user_service.get_user(db, user_id)
    require_can_manage_user(current_user, target)
    return await user_service.update_user(db, user_id, data)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    target = await user_service.get_user(db, user_id)
    require_can_delete_user(current_user, target)
    await user_service.delete_user(db, user_id)
    return MessageResponse(message="User deleted successfully")


@router.post("/{user_id}/activate", response_model=UserRead)
async def activate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    target = await user_service.get_user(db, user_id)
    require_can_manage_user(current_user, target)
    return await user_service.activate_user(db, user_id)


@router.post("/{user_id}/deactivate", response_model=UserRead)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    target = await user_service.get_user(db, user_id)
    require_can_manage_user(current_user, target)
    return await user_service.deactivate_user(db, user_id)


@router.patch("/{user_id}/role", response_model=UserRead)
async def change_role(
    user_id: uuid.UUID,
    data: UserRoleChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    target = await user_service.get_user(db, user_id)
    require_can_change_role(current_user, target, data.role)
    return await user_service.change_role(db, user_id, data.role)


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_or_super),
):
    target = await user_service.get_user(db, user_id)
    require_can_reset_password(current_user, target)
    user, temporary_password = await user_service.reset_password(db, user_id)
    return ResetPasswordResponse(
        id=user.id,
        temporary_password=temporary_password,
    )
