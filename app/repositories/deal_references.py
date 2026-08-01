from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.matrix import Apartment, Building, Floor, Project, Section
from app.models.user import User, UserRole


class DealReferenceRepository:
    async def get_client(self, db: AsyncSession, client_id: uuid.UUID) -> User | None:
        result = await db.execute(
            select(User).where(User.id == client_id, User.role == UserRole.CLIENT, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_manager(self, db: AsyncSession, manager_id: uuid.UUID) -> User | None:
        result = await db.execute(
            select(User).where(
                User.id == manager_id,
                User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.MANAGER]),
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_lead(self, db: AsyncSession, lead_id: uuid.UUID) -> Lead | None:
        result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None)))
        return result.scalar_one_or_none()

    async def get_apartment(self, db: AsyncSession, apartment_id: uuid.UUID) -> Apartment | None:
        return await db.get(Apartment, apartment_id)

    async def get_project(self, db: AsyncSession, project_id: uuid.UUID) -> Project | None:
        return await db.get(Project, project_id)

    async def get_building(self, db: AsyncSession, building_id: uuid.UUID) -> Building | None:
        return await db.get(Building, building_id)

    async def get_section(self, db: AsyncSession, section_id: uuid.UUID) -> Section | None:
        return await db.get(Section, section_id)

    async def get_floor(self, db: AsyncSession, floor_id: uuid.UUID) -> Floor | None:
        return await db.get(Floor, floor_id)


deal_reference_repo = DealReferenceRepository()
