from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.repositories.deal import deal_repo
from app.repositories.deal_activity import deal_activity_repo
from app.repositories.deal_payment import deal_payment_repo
from app.repositories.deal_task import deal_task_repo
from app.services.deal import RESERVATION_WARNING_HOURS, deal_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DashboardService:
    async def get_dashboard(self, db: AsyncSession, actor: User) -> dict:
        await deal_service.expire_overdue_reservations(db)
        now = _now()
        scope_manager_id = actor.id if actor.role == UserRole.MANAGER else None
        scope_client_id = actor.id if actor.role == UserRole.CLIENT else None

        recent_deals, _ = await deal_repo.list(
            db,
            skip=0,
            limit=5,
            sort="newest",
            scope_manager_id=scope_manager_id,
            scope_client_id=scope_client_id,
        )

        recent_activities = await deal_activity_repo.list_recent(
            db, limit=5, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id
        )
        recent_payments = await deal_payment_repo.list_recent(
            db, limit=5, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id
        )

        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        todays_tasks = await deal_task_repo.list_with_deadline(
            db,
            start=start_of_day,
            end=end_of_day,
            completed=False,
            limit=5,
            scope_manager_id=scope_manager_id,
            scope_client_id=scope_client_id,
        )
        late_tasks = await deal_task_repo.list_late(
            db, now=now, limit=5, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id
        )

        upcoming_meetings = await deal_activity_repo.list_upcoming_meetings(
            db, now=now, limit=5, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id
        )

        reservation_expiring = await deal_repo.list_reservation_expiring(
            db,
            now=now + timedelta(hours=RESERVATION_WARNING_HOURS),
            limit=5,
            scope_manager_id=scope_manager_id,
            scope_client_id=scope_client_id,
        )

        return {
            "recent_deals": recent_deals,
            "recent_activities": recent_activities,
            "recent_payments": recent_payments,
            "todays_tasks": todays_tasks,
            "late_tasks": late_tasks,
            "upcoming_meetings": upcoming_meetings,
            "reservation_expiring": reservation_expiring,
        }


dashboard_service = DashboardService()
