import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.repositories.user import user_repo
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    async def create_user(self, db: AsyncSession, data: UserCreate) -> User:
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
            "role": data.role,
        }
        return await user_repo.create(db, user_data)

    async def update_user(
        self, db: AsyncSession, user_id: uuid.UUID, data: UserUpdate
    ) -> User:
        user = await user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFound("User not found")

        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] != user.email:
            existing = await user_repo.get_by_email(db, update_data["email"])
            if existing:
                raise Conflict("Email already in use")

        if "phone" in update_data and update_data["phone"] != user.phone:
            existing = await user_repo.get_by_phone(db, update_data["phone"])
            if existing:
                raise Conflict("Phone already in use")

        return await user_repo.update(db, user, update_data)

    async def delete_user(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        user = await user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFound("User not found")
        await user_repo.soft_delete(db, user)

    async def activate_user(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        user = await user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFound("User not found")
        return await user_repo.update(db, user, {"is_active": True})

    async def deactivate_user(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        user = await user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFound("User not found")
        return await user_repo.update(db, user, {"is_active": False})

    async def change_role(
        self, db: AsyncSession, user_id: uuid.UUID, role: UserRole
    ) -> User:
        user = await user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFound("User not found")
        return await user_repo.update(db, user, {"role": role})

    async def update_profile(
        self, db: AsyncSession, user: User, data: UserUpdate
    ) -> User:
        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] != user.email:
            existing = await user_repo.get_by_email(db, update_data["email"])
            if existing:
                raise Conflict("Email already in use")

        if "phone" in update_data and update_data["phone"] != user.phone:
            existing = await user_repo.get_by_phone(db, update_data["phone"])
            if existing:
                raise Conflict("Phone already in use")

        return await user_repo.update(db, user, update_data)

    async def change_password(
        self, db: AsyncSession, user: User, current_password: str, new_password: str
    ) -> User:
        from app.core.security import verify_password as check_pass

        if not check_pass(current_password, user.password_hash):
            raise Conflict("Current password is incorrect")
        return await user_repo.update(
            db, user, {"password_hash": hash_password(new_password)}
        )

    async def get_user(self, db: AsyncSession, user_id: uuid.UUID) -> User:
        user = await user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFound("User not found")
        return user

    async def list_users(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        skip = (page - 1) * size
        return await user_repo.list(
            db, skip=skip, limit=size, role=role, is_active=is_active, search=search
        )


user_service = UserService()
