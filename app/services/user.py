import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound
from app.core.security import generate_temporary_password, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user import user_repo
from app.schemas.user import UserCreate, UserUpdate
from app.services.email import email_service


class UserService:
    async def create_user(self, db: AsyncSession, data: UserCreate) -> tuple[User, str]:
        existing_email = await user_repo.get_by_email(db, data.email)
        if existing_email:
            raise Conflict("Email already registered")

        existing_phone = await user_repo.get_by_phone(db, data.phone)
        if existing_phone:
            raise Conflict("Phone already registered")

        temporary_password = generate_temporary_password()

        user_data = {
            "first_name": data.first_name,
            "last_name": data.last_name,
            "email": data.email,
            "phone": data.phone,
            "password_hash": hash_password(temporary_password),
            "role": data.role,
        }
        user = await user_repo.create(db, user_data)

        await email_service.send_account_created(
            email=user.email,
            first_name=user.first_name,
            phone=user.phone,
            temporary_password=temporary_password,
        )

        return user, temporary_password

    async def update_user(self, db: AsyncSession, user_id: uuid.UUID, data: UserUpdate) -> User:
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

    async def change_role(self, db: AsyncSession, user_id: uuid.UUID, new_role: UserRole) -> User:
        user = await user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFound("User not found")
        return await user_repo.update(db, user, {"role": new_role})

    async def reset_password(self, db: AsyncSession, user_id: uuid.UUID) -> tuple[User, str]:
        user = await user_repo.get_by_id(db, user_id)
        if not user:
            raise NotFound("User not found")

        temporary_password = generate_temporary_password()
        updated = await user_repo.update(db, user, {"password_hash": hash_password(temporary_password)})

        await email_service.send_password_reset(
            email=user.email,
            first_name=user.first_name,
            phone=user.phone,
            temporary_password=temporary_password,
        )

        return updated, temporary_password

    async def update_profile(self, db: AsyncSession, user: User, data: UserUpdate) -> User:
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

    async def change_password(self, db: AsyncSession, user: User, current_password: str, new_password: str) -> User:
        if not verify_password(current_password, user.password_hash):
            raise Conflict("Current password is incorrect")
        return await user_repo.update(db, user, {"password_hash": hash_password(new_password)})

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
        return await user_repo.list(db, skip=skip, limit=size, role=role, is_active=is_active, search=search)


user_service = UserService()
