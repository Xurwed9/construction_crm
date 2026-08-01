from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deal_timeline import DealTimeline


class DealTimelineRepository:
    async def create(self, db: AsyncSession, data: dict) -> DealTimeline:
        entry = DealTimeline(**data)
        db.add(entry)
        await db.flush()
        return entry

    async def list_by_deal(self, db: AsyncSession, deal_id: uuid.UUID) -> list[DealTimeline]:
        result = await db.execute(
            select(DealTimeline)
            .options(selectinload(DealTimeline.actor))
            .where(DealTimeline.deal_id == deal_id)
            .order_by(DealTimeline.created_at.asc())
        )
        return list(result.scalars().all())

    async def latest_by_deal(self, db: AsyncSession, deal_id: uuid.UUID, limit: int = 10) -> list[DealTimeline]:
        result = await db.execute(
            select(DealTimeline)
            .options(selectinload(DealTimeline.actor))
            .where(DealTimeline.deal_id == deal_id)
            .order_by(DealTimeline.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


deal_timeline_repo = DealTimelineRepository()
