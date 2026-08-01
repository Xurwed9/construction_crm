import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserShortRead


class DealTimelineRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    event: str
    old_value: str | None
    new_value: str | None
    performed_by: uuid.UUID | None
    created_at: datetime
    actor: UserShortRead | None

    model_config = {"from_attributes": True}
