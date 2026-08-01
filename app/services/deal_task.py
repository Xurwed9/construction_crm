from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFound
from app.models.deal_task import DealTask
from app.models.deal_timeline import DealEvent
from app.models.user import User
from app.repositories.deal_references import deal_reference_repo
from app.repositories.deal_task import deal_task_repo
from app.schemas.deal_task import DealTaskCreate, DealTaskUpdate
from app.services.deal import deal_service
from app.services.deal_timeline import timeline_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TaskService:
    async def create(self, db: AsyncSession, actor: User, deal_id: uuid.UUID, data: DealTaskCreate) -> DealTask:
        deal = await deal_service.get_deal_for_write(db, actor, deal_id)
        if data.assigned_to:
            assignee = await deal_reference_repo.get_manager(db, data.assigned_to)
            if not assignee:
                raise NotFound("Assignee not found or is not a manager")
        task = await deal_task_repo.create(
            db,
            {
                "deal_id": deal_id,
                "title": data.title,
                "description": data.description,
                "deadline": data.deadline,
                "priority": data.priority,
                "assigned_to": data.assigned_to,
                "created_by": actor.id,
            },
        )
        timeline_service.record(db, deal.id, DealEvent.TASK_CREATED, new_value=data.title, performed_by=actor.id)
        return task

    async def list(self, db: AsyncSession, actor: User, deal_id: uuid.UUID) -> list[DealTask]:
        await deal_service.get_deal_for_read(db, actor, deal_id)
        return await deal_task_repo.list_by_deal(db, deal_id)

    async def update(self, db: AsyncSession, actor: User, task_id: uuid.UUID, data: DealTaskUpdate) -> DealTask:
        task = await self._get_task_or_404(db, task_id)
        deal = await deal_service.get_deal_for_write(db, actor, task.deal_id)

        update_data = data.model_dump(exclude_unset=True)
        if update_data.get("assigned_to"):
            assignee = await deal_reference_repo.get_manager(db, update_data["assigned_to"])
            if not assignee:
                raise NotFound("Assignee not found or is not a manager")

        old_title = task.title
        was_completed = task.completed
        if update_data.get("completed") and not was_completed:
            update_data["completed_at"] = _now()
        elif not update_data.get("completed", True) and was_completed:
            update_data["completed_at"] = None

        updated = await deal_task_repo.update(db, task, update_data)
        if updated.completed and not was_completed:
            timeline_service.record(db, deal.id, DealEvent.TASK_COMPLETED, old_value=old_title, performed_by=actor.id)
        else:
            timeline_service.record(db, deal.id, DealEvent.TASK_UPDATED, old_value=old_title, performed_by=actor.id)
        return updated

    async def delete(self, db: AsyncSession, actor: User, task_id: uuid.UUID) -> None:
        task = await self._get_task_or_404(db, task_id)
        deal = await deal_service.get_deal_for_write(db, actor, task.deal_id)
        await deal_task_repo.delete(db, task)
        timeline_service.record(db, deal.id, DealEvent.TASK_DELETED, old_value=task.title, performed_by=actor.id)

    async def _get_task_or_404(self, db: AsyncSession, task_id: uuid.UUID) -> DealTask:
        task = await deal_task_repo.get_by_id(db, task_id)
        if not task:
            raise NotFound("Task not found")
        return task


task_service = TaskService()
