import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.deal_activity import DealActivityType
from app.schemas.user import UserShortRead


class DealActivityCreate(BaseModel):
    activity_type: DealActivityType
    content: str = Field(..., min_length=1, max_length=10000)
    is_public: bool = False
    scheduled_at: datetime | None = None


class DealActivityUpdate(BaseModel):
    activity_type: DealActivityType | None = None
    content: str | None = Field(None, min_length=1, max_length=10000)
    is_public: bool | None = None
    scheduled_at: datetime | None = None
    completed: bool | None = None


class DealActivityRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    activity_type: DealActivityType
    content: str
    is_public: bool
    scheduled_at: datetime | None
    completed: bool
    completed_at: datetime | None
    performed_by: uuid.UUID | None
    performed_at: datetime
    created_at: datetime
    updated_at: datetime
    actor: UserShortRead | None

    model_config = {"from_attributes": True}
