from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Forbidden, NotFound
from app.models.deal_activity import DealActivity
from app.models.deal_timeline import DealEvent
from app.models.user import User, UserRole
from app.repositories.deal_activity import deal_activity_repo
from app.schemas.deal_activity import DealActivityCreate, DealActivityUpdate
from app.services.deal import deal_service
from app.services.deal_timeline import timeline_service


class ActivityService:
    async def create(self, db: AsyncSession, actor: User, deal_id: uuid.UUID, data: DealActivityCreate) -> DealActivity:
        await deal_service.get_deal_for_write(db, actor, deal_id)
        activity = await deal_activity_repo.create(
            db,
            {
                "deal_id": deal_id,
                "activity_type": data.activity_type,
                "content": data.content,
                "is_public": data.is_public,
                "scheduled_at": data.scheduled_at,
                "performed_by": actor.id,
            },
        )
        timeline_service.record(
            db,
            deal_id,
            DealEvent.ACTIVITY_ADDED,
            new_value=data.activity_type.value,
            performed_by=actor.id,
        )
        return activity

    async def list(self, db: AsyncSession, actor: User, deal_id: uuid.UUID) -> list[DealActivity]:
        await deal_service.get_deal_for_read(db, actor, deal_id)
        return await deal_activity_repo.list_by_deal(db, deal_id, is_public_only=actor.role == UserRole.CLIENT)

    async def update(
        self, db: AsyncSession, actor: User, activity_id: uuid.UUID, data: DealActivityUpdate
    ) -> DealActivity:
        activity = await self._get_activity_or_404(db, activity_id)
        deal = await deal_service.get_deal_for_write(db, actor, activity.deal_id)
        self._ensure_editable(actor, activity)

        update_data = data.model_dump(exclude_unset=True)
        old_type = activity.activity_type
        if update_data.get("completed") and not activity.completed:
            update_data["completed_at"] = activity.scheduled_at or activity.performed_at
        updated = await deal_activity_repo.update(db, activity, update_data)
        timeline_service.record(
            db,
            deal.id,
            DealEvent.ACTIVITY_UPDATED,
            old_value=old_type.value if old_type != updated.activity_type else None,
            new_value=updated.activity_type.value if old_type != updated.activity_type else None,
            performed_by=actor.id,
        )
        return updated

    async def delete(self, db: AsyncSession, actor: User, activity_id: uuid.UUID) -> None:
        activity = await self._get_activity_or_404(db, activity_id)
        deal = await deal_service.get_deal_for_write(db, actor, activity.deal_id)
        self._ensure_editable(actor, activity)
        await deal_activity_repo.delete(db, activity)
        timeline_service.record(db, deal.id, DealEvent.ACTIVITY_DELETED, performed_by=actor.id)

    async def _get_activity_or_404(self, db: AsyncSession, activity_id: uuid.UUID) -> DealActivity:
        activity = await deal_activity_repo.get_by_id(db, activity_id)
        if not activity:
            raise NotFound("Activity not found")
        return activity

    @staticmethod
    def _ensure_editable(actor: User, activity: DealActivity) -> None:
        if actor.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN) and activity.performed_by != actor.id:
            raise Forbidden("You can only edit your own activities")


activity_service = ActivityService()
