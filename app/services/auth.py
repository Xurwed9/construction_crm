import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, Forbidden, NotFound, Unauthorized
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.repositories.user import user_repo
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthService:
    async def register(self, db: AsyncSession, data: RegisterRequest) -> tuple[str, str, User]:
        existing_email = await user_repo.get_by_email(db, data.email)
        if existing_email:
            raise Conflict("Email already registered")

        existing_phone = await user_repo.get_by_phone(db, data.phone)
        if existing_phone:
            raise Conflict("Phone already registered")

        user_data = {
            "first_name": data.first_name,
            "last_name": data.last_name,
            "email": data.email,
            "phone": data.phone,
            "password_hash": hash_password(data.password),
            "role": UserRole.CLIENT,
        }
        user = await user_repo.create(db, user_data)

        access_token = create_access_token(str(user.id), user.role.value)
        refresh_token_str = self._store_refresh_token(db, user.id)

        return access_token, refresh_token_str, user

    async def login(self, db: AsyncSession, data: LoginRequest) -> tuple[str, str, User]:
        user = await user_repo.get_by_email(db, data.email)
        if not user:
            raise Unauthorized("Invalid email or password")

        if not user.is_active:
            raise Forbidden("Account is deactivated")

        if not verify_password(data.password, user.password_hash):
            raise Unauthorized("Invalid email or password")

        user.last_login = datetime.now(timezone.utc)
        await db.flush()

        access_token = create_access_token(str(user.id), user.role.value)
        refresh_token_str = self._store_refresh_token(db, user.id)

        return access_token, refresh_token_str, user

    async def refresh(self, db: AsyncSession, token_str: str) -> tuple[str, str]:
        payload = decode_token(token_str)
        if not payload or payload.get("type") != "refresh":
            raise Unauthorized("Invalid refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise Unauthorized("Invalid refresh token")

        stored = await self._get_valid_refresh_token(db, token_str)
        if not stored:
            raise Unauthorized("Refresh token revoked or expired")

        user = await user_repo.get_by_id(db, uuid.UUID(user_id))
        if not user or not user.is_active:
            raise Unauthorized("User not found or inactive")

        stored.is_revoked = True
        await db.flush()

        new_access = create_access_token(user_id, user.role.value)
        new_refresh = self._store_refresh_token(db, user.id)

        return new_access, new_refresh

    async def logout(self, db: AsyncSession, token_str: str) -> None:
        stored = await self._get_valid_refresh_token(db, token_str)
        if stored:
            stored.is_revoked = True
            await db.flush()

    async def logout_all(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False,
            )
        )
        tokens = result.scalars().all()
        for token in tokens:
            token.is_revoked = True
        await db.flush()

    async def get_current_user(self, db: AsyncSession, user_id: str) -> User:
        user = await user_repo.get_by_id(db, uuid.UUID(user_id))
        if not user:
            raise NotFound("User not found")
        if not user.is_active:
            raise Forbidden("Account is deactivated")
        return user

    def _store_refresh_token(self, db: AsyncSession, user_id: uuid.UUID) -> str:
        token_str = create_refresh_token(str(user_id), "")
        token = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(token_str),
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(token)
        return token_str

    async def _get_valid_refresh_token(self, db: AsyncSession, token_str: str) -> RefreshToken | None:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(token_str),
                RefreshToken.is_revoked == False,
            )
        )
        stored = result.scalar_one_or_none()
        if not stored:
            return None
        expires_at = stored.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None
        return stored


auth_service = AuthService()
