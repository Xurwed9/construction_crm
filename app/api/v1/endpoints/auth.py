from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.common import MessageResponse
from app.schemas.user import ChangePasswordRequest, UserRead, UserUpdate
from app.services.auth import auth_service
from app.services.user import user_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    access_token, refresh_token, _ = await auth_service.login(db, data)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    access_token, refresh_token = await auth_service.refresh(db, data.refresh_token)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await auth_service.logout(db, data.refresh_token)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserRead)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await user_service.update_profile(db, current_user, data)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await user_service.change_password(db, current_user, data.current_password, data.new_password)
    return MessageResponse(message="Password changed successfully")
