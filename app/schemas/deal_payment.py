import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.deal_payment import DealPaymentMethod


class DealPaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_method: DealPaymentMethod = DealPaymentMethod.CASH
    paid_at: datetime | None = None
    note: str | None = Field(None, max_length=5000)


class DealPaymentRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    amount: float
    payment_method: DealPaymentMethod
    paid_at: datetime
    note: str | None
    created_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
