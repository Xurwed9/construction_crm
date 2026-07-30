import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import Conflict, NotFound
from app.models.matrix import Apartment, ApartmentStatus, Building, Floor, Project, Section
from app.repositories.matrix import (
    apartment_repo,
    building_repo,
    floor_repo,
    project_repo,
    section_repo,
)
from app.schemas.matrix import (
    ApartmentCreate,
    ApartmentUpdate,
    BuildingCreate,
    FloorCreate,
    ProjectCreate,
    ProjectUpdate,
    SectionCreate,
)


class MatrixService:
    async def create_project(self, db: AsyncSession, data: ProjectCreate) -> Project:
        return await project_repo.create(db, data.model_dump())

    async def update_project(self, db: AsyncSession, project_id: uuid.UUID, data: ProjectUpdate) -> Project:
        project = await project_repo.get_by_id(db, project_id)
        if not project:
            raise NotFound("Project not found")
        update_data = data.model_dump(exclude_unset=True)
        return await project_repo.update(db, project, update_data)

    async def get_project(self, db: AsyncSession, project_id: uuid.UUID) -> Project:
        project = await project_repo.get_by_id(db, project_id)
        if not project:
            raise NotFound("Project not found")
        return project

    async def list_projects(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> tuple[list[Project], int]:
        return await project_repo.list(db, skip=skip, limit=limit)

    async def create_building(self, db: AsyncSession, data: BuildingCreate) -> Building:
        project = await project_repo.get_by_id(db, data.project_id)
        if not project:
            raise NotFound("Project not found")
        return await building_repo.create(db, data.model_dump())

    async def get_building(self, db: AsyncSession, building_id: uuid.UUID) -> Building:
        building = await building_repo.get_by_id(db, building_id)
        if not building:
            raise NotFound("Building not found")
        return building

    async def list_buildings(self, db: AsyncSession, project_id: uuid.UUID | None = None) -> tuple[list[Building], int]:
        if project_id:
            buildings = await building_repo.list_by_project(db, project_id)
            return buildings, len(buildings)
        return await building_repo.list(db)

    async def create_section(self, db: AsyncSession, data: SectionCreate) -> Section:
        building = await building_repo.get_by_id(db, data.building_id)
        if not building:
            raise NotFound("Building not found")
        return await section_repo.create(db, data.model_dump())

    async def list_sections(self, db: AsyncSession, building_id: uuid.UUID) -> list[Section]:
        return await section_repo.list_by_building(db, building_id)

    async def create_floor(self, db: AsyncSession, data: FloorCreate) -> Floor:
        building = await building_repo.get_by_id(db, data.building_id)
        if not building:
            raise NotFound("Building not found")
        existing = await floor_repo.get_by_building_and_number(db, data.building_id, data.number)
        if existing:
            raise Conflict(f"Floor {data.number} already exists in this building")
        return await floor_repo.create(db, data.model_dump())

    async def list_floors(self, db: AsyncSession, building_id: uuid.UUID) -> list[Floor]:
        return await floor_repo.list_by_building(db, building_id)

    async def create_apartment(self, db: AsyncSession, data: ApartmentCreate) -> Apartment:
        floor = await floor_repo.get_by_id(db, data.floor_id)
        if not floor:
            raise NotFound("Floor not found")

        existing = await apartment_repo.get_by_building_floor_and_number(db, data.floor_id, data.number)
        if existing:
            raise Conflict(f"Apartment {data.number} already exists on this floor")

        if data.section_id:
            section = await section_repo.get_by_id(db, data.section_id)
            if not section:
                raise NotFound("Section not found")

        return await apartment_repo.create(db, data.model_dump())

    async def update_apartment(self, db: AsyncSession, apartment_id: uuid.UUID, data: ApartmentUpdate) -> Apartment:
        apartment = await apartment_repo.get_by_id(db, apartment_id)
        if not apartment:
            raise NotFound("Apartment not found")
        update_data = data.model_dump(exclude_unset=True)
        return await apartment_repo.update(db, apartment, update_data)

    async def get_apartment(self, db: AsyncSession, apartment_id: uuid.UUID) -> Apartment:
        apartment = await apartment_repo.get_by_id(db, apartment_id)
        if not apartment:
            raise NotFound("Apartment not found")
        return apartment

    async def list_apartments(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        rooms: int | None = None,
        area_min: float | None = None,
        area_max: float | None = None,
        price_min: float | None = None,
        price_max: float | None = None,
        status: ApartmentStatus | None = None,
        floor_number: int | None = None,
        building_id: uuid.UUID | None = None,
    ) -> tuple[list[Apartment], int]:
        return await apartment_repo.list_filtered(
            db,
            skip=skip,
            limit=limit,
            rooms=rooms,
            area_min=area_min,
            area_max=area_max,
            price_min=price_min,
            price_max=price_max,
            status=status,
            floor_number=floor_number,
            building_id=building_id,
        )

    async def reserve_apartment(self, db: AsyncSession, apartment_id: uuid.UUID) -> Apartment:
        apartment = await apartment_repo.get_by_id_with_floor(db, apartment_id)
        if not apartment:
            raise NotFound("Apartment not found")

        if apartment.status != ApartmentStatus.AVAILABLE:
            raise Conflict(
                f"Cannot reserve apartment {apartment.number}: "
                f"current status is '{apartment.status.value}'. "
                f"Only AVAILABLE apartments can be reserved."
            )

        return await apartment_repo.update(db, apartment, {"status": ApartmentStatus.RESERVED})

    async def get_matrix(self, db: AsyncSession, building_id: uuid.UUID) -> dict:
        building = await building_repo.get_by_id(db, building_id)
        if not building:
            raise NotFound("Building not found")

        project = await project_repo.get_by_id(db, building.project_id)
        sections = await section_repo.list_by_building(db, building_id)
        floors = await floor_repo.list_by_building(db, building_id)
        apartments = await apartment_repo.list_by_building(db, building_id)

        apartment_map: dict[uuid.UUID, list[Apartment]] = {}
        for apt in apartments:
            apartment_map.setdefault(apt.floor_id, []).append(apt)

        matrix_sections = []
        for section in sections:
            section_floors = []
            for floor in floors:
                floor_apartments = [
                    {
                        "id": apt.id,
                        "number": apt.number,
                        "rooms": apt.rooms,
                        "area": apt.area,
                        "price": apt.price,
                        "currency": apt.currency,
                        "status": apt.status,
                        "direction": apt.direction,
                        "deal_id": apt.deal_id,
                        "section_id": apt.section_id,
                    }
                    for apt in apartment_map.get(floor.id, [])
                    if apt.section_id == section.id
                ]
                if floor_apartments:
                    section_floors.append(
                        {
                            "floor_number": floor.number,
                            "apartments": floor_apartments,
                        }
                    )

            matrix_sections.append(
                {
                    "section_id": section.id,
                    "section_name": section.name,
                    "floors": section_floors,
                }
            )

        if not sections:
            for floor in floors:
                matrix_sections.append(
                    {
                        "section_id": None,
                        "section_name": "",
                        "floors": [
                            {
                                "floor_number": floor.number,
                                "apartments": [
                                    {
                                        "id": apt.id,
                                        "number": apt.number,
                                        "rooms": apt.rooms,
                                        "area": apt.area,
                                        "price": apt.price,
                                        "currency": apt.currency,
                                        "status": apt.status,
                                        "direction": apt.direction,
                                        "deal_id": apt.deal_id,
                                        "section_id": apt.section_id,
                                    }
                                    for apt in apartment_map.get(floor.id, [])
                                ],
                            }
                        ],
                    }
                )

        return {
            "building_id": building.id,
            "building_name": building.name,
            "project_name": project.name if project else "",
            "sections": matrix_sections,
        }

    async def get_statistics(self, db: AsyncSession, building_id: uuid.UUID) -> dict:
        building = await building_repo.get_by_id(db, building_id)
        if not building:
            raise NotFound("Building not found")
        return await apartment_repo.get_statistics(db, building_id)


matrix_service = MatrixService()
