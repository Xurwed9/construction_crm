import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.lead import LeadPriority, LeadStatus
from app.schemas.user import UserShortRead

PHONE_PATTERN = re.compile(r"^\+?[0-9\s\-()]{7,20}$")


class LeadCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=7, max_length=20)
    email: EmailStr | None = None
    budget: float | None = Field(None, ge=0)
    priority: LeadPriority = LeadPriority.MEDIUM
    lead_source: str | None = Field(None, max_length=100)
    notes: str | None = None
    assigned_manager_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    building_id: uuid.UUID | None = None
    apartment_id: uuid.UUID | None = None
    next_meeting_at: datetime | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not PHONE_PATTERN.match(value):
            raise ValueError("Invalid phone number format")
        return value


class LeadUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    phone: str | None = Field(None, min_length=7, max_length=20)
    email: EmailStr | None = None
    budget: float | None = Field(None, ge=0)
    priority: LeadPriority | None = None
    lead_source: str | None = Field(None, max_length=100)
    notes: str | None = None
    project_id: uuid.UUID | None = None
    building_id: uuid.UUID | None = None
    apartment_id: uuid.UUID | None = None
    next_meeting_at: datetime | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not PHONE_PATTERN.match(value):
            raise ValueError("Invalid phone number format")
        return value


class LeadShortRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    full_name: str
    phone: str
    email: str | None
    budget: float | None
    priority: LeadPriority
    status: LeadStatus
    lead_source: str | None
    assigned_manager_id: uuid.UUID | None
    project_id: uuid.UUID | None
    building_id: uuid.UUID | None
    apartment_id: uuid.UUID | None
    next_meeting_at: datetime | None
    last_activity_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadRead(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    full_name: str
    phone: str
    email: str | None
    budget: float | None
    priority: LeadPriority
    status: LeadStatus
    lead_source: str | None
    notes: str | None
    assigned_manager_id: uuid.UUID | None
    project_id: uuid.UUID | None
    building_id: uuid.UUID | None
    apartment_id: uuid.UUID | None
    next_meeting_at: datetime | None
    last_activity_at: datetime | None
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    assigned_manager: UserShortRead | None

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    items: list[LeadShortRead]
    total: int
    page: int
    size: int
    pages: int


class LeadMoveRequest(BaseModel):
    status: LeadStatus


class LeadAssignManagerRequest(BaseModel):
    assigned_manager_id: uuid.UUID


class LeadNoteCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class LeadNoteUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


class LeadNoteRead(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    author_id: uuid.UUID | None
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadTimelineRead(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    action: str
    description: str | None
    actor_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KanbanColumn(BaseModel):
    status: LeadStatus
    count: int
    leads: list[LeadShortRead]
