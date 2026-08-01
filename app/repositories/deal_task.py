from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deal import Deal
from app.models.deal_task import DealTask

ASSIGNEE_LOAD = selectinload(DealTask.assignee)


class DealTaskRepository:
    async def get_by_id(self, db: AsyncSession, task_id: uuid.UUID) -> DealTask | None:
        result = await db.execute(select(DealTask).options(ASSIGNEE_LOAD).where(DealTask.id == task_id))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> DealTask:
        task = DealTask(**data)
        db.add(task)
        await db.flush()
        return task

    async def update(self, db: AsyncSession, task: DealTask, data: dict) -> DealTask:
        for key, value in data.items():
            setattr(task, key, value)
        await db.flush()
        return task

    async def delete(self, db: AsyncSession, task: DealTask) -> None:
        await db.delete(task)
        await db.flush()

    async def list_by_deal(self, db: AsyncSession, deal_id: uuid.UUID) -> list[DealTask]:
        result = await db.execute(
            select(DealTask)
            .options(ASSIGNEE_LOAD)
            .where(DealTask.deal_id == deal_id)
            .order_by(DealTask.deadline.asc().nulls_last(), DealTask.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_with_deadline(
        self,
        db: AsyncSession,
        *,
        start: datetime,
        end: datetime,
        completed: bool = False,
        limit: int = 5,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> list[DealTask]:
        query = (
            select(DealTask)
            .join(Deal, Deal.id == DealTask.deal_id)
            .where(
                Deal.deleted_at.is_(None),
                DealTask.deadline.is_not(None),
                DealTask.deadline >= start,
                DealTask.deadline <= end,
                DealTask.completed.is_(completed),
            )
        )
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        result = await db.execute(query.options(ASSIGNEE_LOAD).order_by(DealTask.deadline.asc()).limit(limit))
        return list(result.scalars().all())

    async def list_late(
        self,
        db: AsyncSession,
        *,
        now: datetime,
        limit: int = 5,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> list[DealTask]:
        query = (
            select(DealTask)
            .join(Deal, Deal.id == DealTask.deal_id)
            .where(
                Deal.deleted_at.is_(None),
                DealTask.deadline.is_not(None),
                DealTask.deadline < now,
                DealTask.completed.is_(False),
            )
        )
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        result = await db.execute(query.options(ASSIGNEE_LOAD).order_by(DealTask.deadline.asc()).limit(limit))
        return list(result.scalars().all())


deal_task_repo = DealTaskRepository()
