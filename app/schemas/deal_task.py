import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.deal_task import TaskPriority
from app.schemas.user import UserShortRead


class DealTaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    deadline: datetime | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_to: uuid.UUID | None = None


class DealTaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    deadline: datetime | None = None
    priority: TaskPriority | None = None
    assigned_to: uuid.UUID | None = None
    completed: bool | None = None


class DealTaskRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    title: str
    description: str | None
    deadline: datetime | None
    priority: TaskPriority
    completed: bool
    completed_at: datetime | None
    assigned_to: uuid.UUID | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    assignee: UserShortRead | None

    model_config = {"from_attributes": True}
