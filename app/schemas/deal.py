import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.models.deal import DealPaymentType, DealPriority, DealStatus
from app.schemas.lead import LeadShortRead
from app.schemas.matrix import ApartmentRead, BuildingRead, ProjectRead
from app.schemas.user import UserShortRead


class DealCreate(BaseModel):
    lead_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    building_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    floor_id: uuid.UUID | None = None
    apartment_id: uuid.UUID | None = None
    priority: DealPriority = DealPriority.MEDIUM
    payment_type: DealPaymentType = DealPaymentType.CASH
    contract_number: str | None = Field(None, max_length=50)
    price: float | None = Field(None, ge=0)
    discount: float = Field(0.0, ge=0)
    currency: str | None = Field(None, min_length=3, max_length=10)
    expected_close_date: datetime | None = None
    description: str | None = None

    @model_validator(mode="after")
    def validate_financials(self) -> "DealCreate":
        if self.price is not None and self.discount > self.price:
            raise ValueError("Discount cannot exceed the price")
        return self


class DealUpdate(BaseModel):
    status: DealStatus | None = None
    client_id: uuid.UUID | None = None
    manager_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    building_id: uuid.UUID | None = None
    section_id: uuid.UUID | None = None
    floor_id: uuid.UUID | None = None
    apartment_id: uuid.UUID | None = None
    priority: DealPriority | None = None
    payment_type: DealPaymentType | None = None
    contract_number: str | None = Field(None, max_length=50)
    price: float | None = Field(None, ge=0)
    discount: float | None = Field(None, ge=0)
    expected_close_date: datetime | None = None
    description: str | None = None


class DealReserveRequest(BaseModel):
    reservation_until: datetime | None = None


class DealCancelRequest(BaseModel):
    cancel_reason: str = Field(..., min_length=1, max_length=5000)


class DealCloseRequest(BaseModel):
    contract_number: str | None = Field(None, max_length=50)


class DealRead(BaseModel):
    id: uuid.UUID
    deal_number: str | None
    lead_id: uuid.UUID | None
    client_id: uuid.UUID | None
    manager_id: uuid.UUID | None
    project_id: uuid.UUID | None
    building_id: uuid.UUID | None
    section_id: uuid.UUID | None
    floor_id: uuid.UUID | None
    apartment_id: uuid.UUID | None
    status: DealStatus
    priority: DealPriority
    payment_type: DealPaymentType
    reservation_until: datetime | None
    reservation_expired: bool
    contract_number: str | None
    price: float
    discount: float
    final_price: float
    paid_amount: float
    remaining_amount: float
    currency: str
    expected_close_date: datetime | None
    closed_at: datetime | None
    cancel_reason: str | None
    description: str | None
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    lead: LeadShortRead | None
    client: UserShortRead | None
    manager: UserShortRead | None
    apartment: ApartmentRead | None
    project: ProjectRead | None
    building: BuildingRead | None

    model_config = {"from_attributes": True}


class DealListResponse(BaseModel):
    items: list[DealRead]
    total: int
    page: int
    size: int
    pages: int
