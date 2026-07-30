import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserCRUD:
    async def get_all(self, db: AsyncSession) -> list[User]:
        result = await db.execute(select(User))
        return list(result.scalars().all())

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        return await db.get(User, user_id)

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: UserCreate) -> User:
        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
        )
        db.add(user)
        await db.flush()
        return user

    async def update(self, db: AsyncSession, user: User, data: UserUpdate) -> User:
        if data.email is not None:
            user.email = data.email
        if data.username is not None:
            user.username = data.username
        if data.password is not None:
            user.hashed_password = hash_password(data.password)
        await db.flush()
        return user

    async def delete(self, db: AsyncSession, user: User) -> None:
        await db.delete(user)
        await db.flush()


user_crud = UserCRUD()
