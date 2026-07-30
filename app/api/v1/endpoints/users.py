import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import RoleChecker
from app.models.user import User, UserRole
from app.permissions.roles import (
    check_can_change_role,
    check_can_create_user,
    check_can_manage_user,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.schemas.user import UserCreate, UserRead, UserShortRead, UserUpdate
from app.services.user import user_service

router = APIRouter(prefix="/users", tags=["Users"])

admin_only = RoleChecker(UserRole.SUPER_ADMIN, UserRole.ADMIN)
super_admin_only = RoleChecker(UserRole.SUPER_ADMIN)


@router.get("/", response_model=PaginatedResponse[UserShortRead])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: UserRole | None = None,
    is_active: bool | None = None,
    search: str | None = Query(None, min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
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
    current_user: User = Depends(admin_only),
):
    return await user_service.get_user(db, user_id)


@router.post("/", response_model=UserRead, status_code=201)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    check_can_create_user(current_user, data.role)
    return await user_service.create_user(db, data)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    target = await user_service.get_user(db, user_id)
    check_can_manage_user(current_user, target)
    return await user_service.update_user(db, user_id, data)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    target = await user_service.get_user(db, user_id)
    check_can_manage_user(current_user, target)
    await user_service.delete_user(db, user_id)
    return MessageResponse(message="User deleted successfully")


@router.post("/{user_id}/activate", response_model=UserRead)
async def activate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    target = await user_service.get_user(db, user_id)
    check_can_manage_user(current_user, target)
    return await user_service.activate_user(db, user_id)


@router.post("/{user_id}/deactivate", response_model=UserRead)
async def deactivate_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(admin_only),
):
    target = await user_service.get_user(db, user_id)
    check_can_manage_user(current_user, target)
    return await user_service.deactivate_user(db, user_id)


@router.patch("/{user_id}/role", response_model=UserRead)
async def change_role(
    user_id: uuid.UUID,
    new_role: UserRole,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(super_admin_only),
):
    target = await user_service.get_user(db, user_id)
    check_can_change_role(current_user, target, new_role)
    return await user_service.change_role(db, user_id, new_role)
