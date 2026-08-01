from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import DealStatus
from app.models.user import User, UserRole
from app.repositories.deal import deal_repo
from app.services.deal import deal_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AnalyticsService:
    async def get_statistics(self, db: AsyncSession, actor: User) -> dict:
        await deal_service.expire_overdue_reservations(db)
        scope_manager_id = actor.id if actor.role == UserRole.MANAGER else None
        scope_client_id = actor.id if actor.role == UserRole.CLIENT else None

        now = _now()
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total = await deal_repo.count(db, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id)
        open_deals = await deal_repo.count(
            db,
            exclude_statuses=[DealStatus.SOLD, DealStatus.CANCELLED],
            scope_manager_id=scope_manager_id,
            scope_client_id=scope_client_id,
        )
        reserved = await deal_repo.count(
            db, status=DealStatus.RESERVED, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id
        )
        sold = await deal_repo.count(
            db, status=DealStatus.SOLD, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id
        )
        cancelled = await deal_repo.count(
            db, status=DealStatus.CANCELLED, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id
        )
        deals_today = await deal_repo.count(
            db,
            date_from=start_of_today,
            scope_manager_id=scope_manager_id,
            scope_client_id=scope_client_id,
        )
        deals_this_month = await deal_repo.count(
            db,
            date_from=start_of_month,
            scope_manager_id=scope_manager_id,
            scope_client_id=scope_client_id,
        )
        revenue = await deal_repo.get_revenue(db, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id)
        average_deal = round(revenue / sold, 2) if sold else 0.0
        conversion_rate = round(sold / total * 100, 2) if total else 0.0
        top_managers = await deal_repo.get_top_managers(
            db, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id
        )
        avg_closing = await deal_repo.get_avg_closing_time_days(
            db, scope_manager_id=scope_manager_id, scope_client_id=scope_client_id
        )

        return {
            "total_deals": total,
            "open_deals": open_deals,
            "reserved": reserved,
            "sold": sold,
            "cancelled": cancelled,
            "deals_today": deals_today,
            "deals_this_month": deals_this_month,
            "revenue": revenue,
            "average_deal": average_deal,
            "conversion_rate": conversion_rate,
            "top_managers": top_managers,
            "average_closing_time_days": avg_closing,
        }


analytics_service = AnalyticsService()
