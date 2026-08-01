import uuid

from pydantic import BaseModel


class ManagerPerformance(BaseModel):
    manager_id: uuid.UUID | None
    manager_name: str | None
    total_deals: int
    sold_deals: int
    revenue: float


class DealStatistics(BaseModel):
    total_deals: int
    open_deals: int
    reserved: int
    sold: int
    cancelled: int
    deals_today: int
    deals_this_month: int
    revenue: float
    average_deal: float
    conversion_rate: float
    top_managers: list[ManagerPerformance]
    average_closing_time_days: float | None
