from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lead import PRIORITY_WEIGHTS, Lead, LeadNote, LeadPriority, LeadStatus, LeadTimeline
from app.models.matrix import Building, Project
from app.models.user import User, UserRole

PRIORITY_ORDER = case(
    *[(Lead.priority == p, w) for p, w in sorted(PRIORITY_WEIGHTS.items(), key=lambda x: x[1])],
    else_=0,
)


def build_lead_filters(
    query,
    *,
    search: str | None = None,
    status: LeadStatus | None = None,
    priority: LeadPriority | None = None,
    manager_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    lead_source: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    scope_manager_id: uuid.UUID | None = None,
):
    if scope_manager_id is not None:
        query = query.where(Lead.assigned_manager_id == scope_manager_id)
    elif manager_id is not None:
        query = query.where(Lead.assigned_manager_id == manager_id)
    if status is not None:
        query = query.where(Lead.status == status)
    if priority is not None:
        query = query.where(Lead.priority == priority)
    if project_id is not None:
        query = query.where(Lead.project_id == project_id)
    if lead_source is not None:
        query = query.where(Lead.lead_source.ilike(f"%{lead_source}%"))
    if date_from is not None:
        query = query.where(Lead.created_at >= date_from)
    if date_to is not None:
        query = query.where(Lead.created_at <= date_to)
    if search:
        pattern = f"%{search}%"
        query = query.where(Lead.full_name.ilike(pattern) | Lead.phone.ilike(pattern) | Lead.email.ilike(pattern))
    return query


def apply_lead_sorting(query, sort: str):
    if sort == "oldest":
        return query.order_by(Lead.created_at.asc())
    if sort == "priority":
        return query.order_by(PRIORITY_ORDER.desc(), Lead.created_at.desc())
    if sort == "budget":
        return query.order_by(Lead.budget.desc().nulls_last(), Lead.created_at.desc())
    return query.order_by(Lead.created_at.desc())


class LeadRepository:
    async def get_by_id(self, db: AsyncSession, lead_id: uuid.UUID) -> Lead | None:
        result = await db.execute(
            select(Lead)
            .options(selectinload(Lead.assigned_manager))
            .where(Lead.id == lead_id, Lead.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> Lead:
        lead = Lead(**data)
        db.add(lead)
        await db.flush()
        await db.refresh(lead)
        return lead

    async def update(self, db: AsyncSession, lead: Lead, data: dict) -> Lead:
        for key, value in data.items():
            setattr(lead, key, value)
        await db.flush()
        await db.refresh(lead)
        return lead

    async def soft_delete(self, db: AsyncSession, lead: Lead) -> Lead:
        lead.deleted_at = func.now()
        await db.flush()
        await db.refresh(lead)
        return lead

    async def list(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: LeadStatus | None = None,
        priority: LeadPriority | None = None,
        manager_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        lead_source: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: str = "newest",
        scope_manager_id: uuid.UUID | None = None,
    ) -> tuple[list[Lead], int]:
        query = select(Lead).where(Lead.deleted_at.is_(None))
        query = build_lead_filters(
            query,
            search=search,
            status=status,
            priority=priority,
            manager_id=manager_id,
            project_id=project_id,
            lead_source=lead_source,
            date_from=date_from,
            date_to=date_to,
            scope_manager_id=scope_manager_id,
        )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        query = apply_lead_sorting(query, sort)
        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total

    async def kanban(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        status: LeadStatus | None = None,
        priority: LeadPriority | None = None,
        manager_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        lead_source: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        scope_manager_id: uuid.UUID | None = None,
    ) -> dict[LeadStatus, list[Lead]]:
        query = select(Lead).where(Lead.deleted_at.is_(None))
        query = build_lead_filters(
            query,
            search=search,
            status=status,
            priority=priority,
            manager_id=manager_id,
            project_id=project_id,
            lead_source=lead_source,
            date_from=date_from,
            date_to=date_to,
            scope_manager_id=scope_manager_id,
        )
        query = query.order_by(PRIORITY_ORDER.desc(), Lead.created_at.desc())

        result = await db.execute(query)
        leads = list(result.scalars().all())

        grouped: dict[LeadStatus, list[Lead]] = {s: [] for s in LeadStatus}
        for lead in leads:
            grouped[lead.status].append(lead)
        return grouped

    async def get_lead_short(self, db: AsyncSession, lead_id: uuid.UUID) -> Lead | None:
        result = await db.execute(select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None)))
        return result.scalar_one_or_none()


class LeadNoteRepository:
    async def get_by_id(self, db: AsyncSession, note_id: uuid.UUID) -> LeadNote | None:
        return await db.get(LeadNote, note_id)

    async def create(self, db: AsyncSession, data: dict) -> LeadNote:
        note = LeadNote(**data)
        db.add(note)
        await db.flush()
        await db.refresh(note)
        return note

    async def update(self, db: AsyncSession, note: LeadNote, data: dict) -> LeadNote:
        for key, value in data.items():
            setattr(note, key, value)
        await db.flush()
        await db.refresh(note)
        return note

    async def delete(self, db: AsyncSession, note: LeadNote) -> None:
        await db.delete(note)
        await db.flush()

    async def list_by_lead(self, db: AsyncSession, lead_id: uuid.UUID) -> list[LeadNote]:
        result = await db.execute(
            select(LeadNote).where(LeadNote.lead_id == lead_id).order_by(LeadNote.created_at.desc())
        )
        return list(result.scalars().all())


class LeadTimelineRepository:
    async def create(self, db: AsyncSession, data: dict) -> LeadTimeline:
        entry = LeadTimeline(**data)
        db.add(entry)
        await db.flush()
        await db.refresh(entry)
        return entry

    async def list_by_lead(self, db: AsyncSession, lead_id: uuid.UUID) -> list[LeadTimeline]:
        result = await db.execute(
            select(LeadTimeline).where(LeadTimeline.lead_id == lead_id).order_by(LeadTimeline.created_at.asc())
        )
        return list(result.scalars().all())


class LeadReferenceRepository:
    async def get_manager(self, db: AsyncSession, user_id: uuid.UUID) -> User | None:
        result = await db.execute(
            select(User).where(
                User.id == user_id,
                User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.MANAGER]),
            )
        )
        return result.scalar_one_or_none()

    async def get_project(self, db: AsyncSession, project_id: uuid.UUID) -> Project | None:
        return await db.get(Project, project_id)

    async def get_building(self, db: AsyncSession, building_id: uuid.UUID) -> Building | None:
        return await db.get(Building, building_id)


lead_repo = LeadRepository()
lead_note_repo = LeadNoteRepository()
lead_timeline_repo = LeadTimelineRepository()
lead_reference_repo = LeadReferenceRepository()
