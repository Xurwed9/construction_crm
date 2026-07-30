import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.matrix import ApartmentStatus, ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    address: str | None = None
    status: ProjectStatus = ProjectStatus.ACTIVE


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    address: str | None = None
    status: ProjectStatus | None = None


class ProjectRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    address: str | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BuildingCreate(BaseModel):
    project_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    number_of_sections: int = Field(default=1, ge=1)
    floors_count: int = Field(..., ge=1)


class BuildingRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    number_of_sections: int
    floors_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SectionCreate(BaseModel):
    building_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=100)


class SectionRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class FloorCreate(BaseModel):
    building_id: uuid.UUID
    number: int = Field(..., ge=0)


class FloorRead(BaseModel):
    id: uuid.UUID
    building_id: uuid.UUID
    number: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ApartmentCreate(BaseModel):
    floor_id: uuid.UUID
    section_id: uuid.UUID | None = None
    number: str = Field(..., min_length=1, max_length=50)
    rooms: int = Field(..., ge=1)
    area: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    currency: str = "USD"
    status: ApartmentStatus = ApartmentStatus.AVAILABLE
    direction: str | None = Field(None, max_length=50)
    description: str | None = None


class ApartmentUpdate(BaseModel):
    number: str | None = Field(None, min_length=1, max_length=50)
    rooms: int | None = Field(None, ge=1)
    area: float | None = Field(None, gt=0)
    price: float | None = Field(None, gt=0)
    currency: str | None = None
    status: ApartmentStatus | None = None
    direction: str | None = Field(None, max_length=50)
    description: str | None = None
    section_id: uuid.UUID | None = None


class ApartmentRead(BaseModel):
    id: uuid.UUID
    floor_id: uuid.UUID
    section_id: uuid.UUID | None
    number: str
    rooms: int
    area: float
    price: float
    currency: str
    status: ApartmentStatus
    direction: str | None
    description: str | None
    deal_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MatrixApartment(BaseModel):
    id: uuid.UUID
    number: str
    rooms: int
    area: float
    price: float
    currency: str
    status: ApartmentStatus
    direction: str | None
    deal_id: uuid.UUID | None
    section_id: uuid.UUID | None


class MatrixFloor(BaseModel):
    floor_number: int
    apartments: list[MatrixApartment]


class MatrixSection(BaseModel):
    section_id: uuid.UUID
    section_name: str
    floors: list[MatrixFloor]


class MatrixResponse(BaseModel):
    building_id: uuid.UUID
    building_name: str
    project_name: str
    sections: list[MatrixSection]


class ApartmentReserveRequest(BaseModel):
    apartment_id: uuid.UUID


class BuildingStatistics(BaseModel):
    total_apartments: int
    available: int
    reserved: int
    sold: int
    blocked: int
    total_revenue: float


class ApartmentFilterParams(BaseModel):
    rooms: int | None = None
    area_min: float | None = None
    area_max: float | None = None
    price_min: float | None = None
    price_max: float | None = None
    status: ApartmentStatus | None = None
    floor_number: int | None = None
    building_id: uuid.UUID | None = None
