import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models.user import User
from app.permissions.roles import MATRIX_CREATE, MATRIX_RESERVE, MATRIX_UPDATE, MATRIX_VIEW
from app.schemas.common import PaginatedResponse
from app.schemas.matrix import (
    ApartmentCreate,
    ApartmentRead,
    ApartmentReserveRequest,
    ApartmentUpdate,
    BuildingCreate,
    BuildingRead,
    BuildingStatistics,
    FloorCreate,
    FloorRead,
    MatrixResponse,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    SectionCreate,
    SectionRead,
)
from app.services.matrix import matrix_service

router = APIRouter(prefix="/matrix", tags=["Apartment Matrix"])


@router.get("/projects", response_model=PaginatedResponse[ProjectRead])
async def list_projects(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    projects, total = await matrix_service.list_projects(db, skip=(page - 1) * size, limit=size)
    pages = (total + size - 1) // size
    return PaginatedResponse(items=projects, total=total, page=page, size=size, pages=pages)


@router.post("/projects", response_model=ProjectRead, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_CREATE)),
):
    return await matrix_service.create_project(db, data)


@router.get("/projects/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    return await matrix_service.get_project(db, project_id)


@router.patch("/projects/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_UPDATE)),
):
    return await matrix_service.update_project(db, project_id, data)


@router.get("/buildings", response_model=PaginatedResponse[BuildingRead])
async def list_buildings(
    project_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    buildings, total = await matrix_service.list_buildings(db, project_id=project_id)
    pages = (total + size - 1) // size
    return PaginatedResponse(items=buildings, total=total, page=page, size=size, pages=pages)


@router.post("/buildings", response_model=BuildingRead, status_code=201)
async def create_building(
    data: BuildingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_CREATE)),
):
    return await matrix_service.create_building(db, data)


@router.get("/buildings/{building_id}", response_model=BuildingRead)
async def get_building(
    building_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    return await matrix_service.get_building(db, building_id)


@router.get("/floors", response_model=list[FloorRead])
async def list_floors(
    building_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    return await matrix_service.list_floors(db, building_id)


@router.post("/floors", response_model=FloorRead, status_code=201)
async def create_floor(
    data: FloorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_CREATE)),
):
    return await matrix_service.create_floor(db, data)


@router.get("/sections", response_model=list[SectionRead])
async def list_sections(
    building_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    return await matrix_service.list_sections(db, building_id)


@router.post("/sections", response_model=SectionRead, status_code=201)
async def create_section(
    data: SectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_CREATE)),
):
    return await matrix_service.create_section(db, data)


@router.get("/apartments", response_model=PaginatedResponse[ApartmentRead])
async def list_apartments(
    rooms: int | None = Query(None),
    area_min: float | None = Query(None),
    area_max: float | None = Query(None),
    price_min: float | None = Query(None),
    price_max: float | None = Query(None),
    status: str | None = Query(None),
    floor_number: int | None = Query(None),
    building_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    apartments, total = await matrix_service.list_apartments(
        db,
        skip=(page - 1) * size,
        limit=size,
        rooms=rooms,
        area_min=area_min,
        area_max=area_max,
        price_min=price_min,
        price_max=price_max,
        status=status,
        floor_number=floor_number,
        building_id=building_id,
    )
    pages = (total + size - 1) // size
    return PaginatedResponse(items=apartments, total=total, page=page, size=size, pages=pages)


@router.post("/apartments", response_model=ApartmentRead, status_code=201)
async def create_apartment(
    data: ApartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_CREATE)),
):
    return await matrix_service.create_apartment(db, data)


@router.get("/apartments/{apartment_id}", response_model=ApartmentRead)
async def get_apartment(
    apartment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    return await matrix_service.get_apartment(db, apartment_id)


@router.patch("/apartments/{apartment_id}", response_model=ApartmentRead)
async def update_apartment(
    apartment_id: uuid.UUID,
    data: ApartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_UPDATE)),
):
    return await matrix_service.update_apartment(db, apartment_id, data)


@router.post("/reserve", response_model=ApartmentRead)
async def reserve_apartment(
    data: ApartmentReserveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_RESERVE)),
):
    return await matrix_service.reserve_apartment(db, data.apartment_id)


@router.get("/matrix/{building_id}", response_model=MatrixResponse)
async def get_matrix(
    building_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    return await matrix_service.get_matrix(db, building_id)


@router.get("/statistics/{building_id}", response_model=BuildingStatistics)
async def get_statistics(
    building_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(MATRIX_VIEW)),
):
    return await matrix_service.get_statistics(db, building_id)
