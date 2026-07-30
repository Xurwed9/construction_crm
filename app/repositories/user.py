import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


class UserRepository:
    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        return await db.get(User, user_id)

    async def get_by_email(self, db: AsyncSession, email: str) -> User | None:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_phone(self, db: AsyncSession, phone: str) -> User | None:
        result = await db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> User:
        user = User(**data)
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    async def update(self, db: AsyncSession, user: User, data: dict) -> User:
        for key, value in data.items():
            setattr(user, key, value)
        await db.flush()
        await db.refresh(user)
        return user

    async def soft_delete(self, db: AsyncSession, user: User) -> User:
        user.deleted_at = func.now()
        await db.flush()
        await db.refresh(user)
        return user

    async def list(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        role: UserRole | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[User], int]:
        query = select(User)

        if role is not None:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        if search:
            pattern = f"%{search}%"
            query = query.where(
                User.first_name.ilike(pattern)
                | User.last_name.ilike(pattern)
                | User.email.ilike(pattern)
                | User.phone.ilike(pattern)
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        query = query.order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        users = list(result.scalars().all())

        return users, total


user_repo = UserRepository()
