from pydantic import BaseModel

from app.schemas.deal import DealRead
from app.schemas.deal_activity import DealActivityRead
from app.schemas.deal_payment import DealPaymentRead
from app.schemas.deal_task import DealTaskRead


class DashboardDeals(BaseModel):
    recent_deals: list[DealRead]
    recent_activities: list[DealActivityRead]
    recent_payments: list[DealPaymentRead]
    todays_tasks: list[DealTaskRead]
    late_tasks: list[DealTaskRead]
    upcoming_meetings: list[DealActivityRead]
    reservation_expiring: list[DealRead]
