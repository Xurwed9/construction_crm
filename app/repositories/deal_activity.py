from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deal import Deal
from app.models.deal_activity import DealActivity, DealActivityType


class DealActivityRepository:
    async def get_by_id(self, db: AsyncSession, activity_id: uuid.UUID) -> DealActivity | None:
        return await db.get(DealActivity, activity_id)

    async def create(self, db: AsyncSession, data: dict) -> DealActivity:
        activity = DealActivity(**data)
        db.add(activity)
        await db.flush()
        return activity

    async def update(self, db: AsyncSession, activity: DealActivity, data: dict) -> DealActivity:
        for key, value in data.items():
            setattr(activity, key, value)
        await db.flush()
        return activity

    async def delete(self, db: AsyncSession, activity: DealActivity) -> None:
        await db.delete(activity)
        await db.flush()

    async def list_by_deal(
        self, db: AsyncSession, deal_id: uuid.UUID, *, is_public_only: bool = False
    ) -> list[DealActivity]:
        query = select(DealActivity).where(DealActivity.deal_id == deal_id)
        if is_public_only:
            query = query.where(DealActivity.is_public.is_(True))
        result = await db.execute(
            query.options(selectinload(DealActivity.actor)).order_by(DealActivity.performed_at.desc())
        )
        return list(result.scalars().all())

    async def count_by_deal(self, db: AsyncSession, deal_id: uuid.UUID) -> int:
        result = await db.execute(select(func.count(DealActivity.id)).where(DealActivity.deal_id == deal_id))
        return result.scalar_one()

    async def list_recent(
        self,
        db: AsyncSession,
        *,
        limit: int = 5,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> list[DealActivity]:
        query = select(DealActivity).where(Deal.deleted_at.is_(None))
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        result = await db.execute(
            query.join(Deal, Deal.id == DealActivity.deal_id)
            .options(selectinload(DealActivity.actor))
            .order_by(DealActivity.performed_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_upcoming_meetings(
        self,
        db: AsyncSession,
        *,
        now: datetime,
        limit: int = 5,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> list[DealActivity]:
        query = (
            select(DealActivity)
            .join(Deal, Deal.id == DealActivity.deal_id)
            .where(
                Deal.deleted_at.is_(None),
                DealActivity.activity_type == DealActivityType.MEETING,
                DealActivity.scheduled_at.is_not(None),
                DealActivity.scheduled_at >= now,
                DealActivity.completed.is_(False),
            )
        )
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        result = await db.execute(
            query.options(selectinload(DealActivity.actor)).order_by(DealActivity.scheduled_at.asc()).limit(limit)
        )
        return list(result.scalars().all())


deal_activity_repo = DealActivityRepository()
