from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal_timeline import DealTimeline
from app.repositories.deal_timeline import deal_timeline_repo
from app.utils.logging import get_logger

logger = get_logger("deals.timeline")


def dispatch(
    db: AsyncSession,
    deal_id: uuid.UUID,
    event: str,
    *,
    old_value: str | None = None,
    new_value: str | None = None,
    performed_by: uuid.UUID | None = None,
    ctx: dict[str, Any] | None = None,
) -> DealTimeline:
    """Record a domain event into the deal timeline and the structured log."""
    entry = DealTimeline(
        deal_id=deal_id,
        event=event,
        old_value=old_value,
        new_value=new_value,
        performed_by=performed_by,
    )
    db.add(entry)
    logger.info(
        "deal.event",
        extra={
            "event": event,
            "ctx": {
                "deal_id": str(deal_id),
                "old_value": old_value,
                "new_value": new_value,
                "performed_by": str(performed_by) if performed_by else None,
                **(ctx or {}),
            },
        },
    )
    return entry


class TimelineService:
    def record(
        self,
        db: AsyncSession,
        deal_id: uuid.UUID,
        event: str,
        *,
        old_value: str | None = None,
        new_value: str | None = None,
        performed_by: uuid.UUID | None = None,
        ctx: dict[str, Any] | None = None,
    ) -> None:
        dispatch(
            db,
            deal_id,
            event,
            old_value=old_value,
            new_value=new_value,
            performed_by=performed_by,
            ctx=ctx,
        )

    async def list_for_deal(self, db: AsyncSession, deal_id: uuid.UUID):
        return await deal_timeline_repo.list_by_deal(db, deal_id)


timeline_service = TimelineService()
