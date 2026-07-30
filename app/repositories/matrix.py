import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.matrix import Apartment, ApartmentStatus, Building, Floor, Project, Section


class ProjectRepository:
    async def get_by_id(self, db: AsyncSession, project_id: uuid.UUID) -> Project | None:
        return await db.get(Project, project_id)

    async def create(self, db: AsyncSession, data: dict) -> Project:
        project = Project(**data)
        db.add(project)
        await db.flush()
        await db.refresh(project)
        return project

    async def update(self, db: AsyncSession, project: Project, data: dict) -> Project:
        for key, value in data.items():
            setattr(project, key, value)
        await db.flush()
        await db.refresh(project)
        return project

    async def list(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> tuple[list[Project], int]:
        query = select(Project)
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()
        result = await db.execute(query.order_by(Project.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total


class BuildingRepository:
    async def get_by_id(self, db: AsyncSession, building_id: uuid.UUID) -> Building | None:
        return await db.get(Building, building_id)

    async def create(self, db: AsyncSession, data: dict) -> Building:
        building = Building(**data)
        db.add(building)
        await db.flush()
        await db.refresh(building)
        return building

    async def list_by_project(self, db: AsyncSession, project_id: uuid.UUID) -> list[Building]:
        result = await db.execute(select(Building).where(Building.project_id == project_id).order_by(Building.name))
        return list(result.scalars().all())

    async def list(self, db: AsyncSession, *, skip: int = 0, limit: int = 100) -> tuple[list[Building], int]:
        query = select(Building)
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()
        result = await db.execute(query.order_by(Building.created_at.desc()).offset(skip).limit(limit))
        return list(result.scalars().all()), total


class SectionRepository:
    async def get_by_id(self, db: AsyncSession, section_id: uuid.UUID) -> Section | None:
        return await db.get(Section, section_id)

    async def create(self, db: AsyncSession, data: dict) -> Section:
        section = Section(**data)
        db.add(section)
        await db.flush()
        await db.refresh(section)
        return section

    async def list_by_building(self, db: AsyncSession, building_id: uuid.UUID) -> list[Section]:
        result = await db.execute(select(Section).where(Section.building_id == building_id).order_by(Section.name))
        return list(result.scalars().all())


class FloorRepository:
    async def get_by_id(self, db: AsyncSession, floor_id: uuid.UUID) -> Floor | None:
        return await db.get(Floor, floor_id)

    async def create(self, db: AsyncSession, data: dict) -> Floor:
        floor = Floor(**data)
        db.add(floor)
        await db.flush()
        await db.refresh(floor)
        return floor

    async def list_by_building(self, db: AsyncSession, building_id: uuid.UUID) -> list[Floor]:
        result = await db.execute(select(Floor).where(Floor.building_id == building_id).order_by(Floor.number.desc()))
        return list(result.scalars().all())

    async def get_by_building_and_number(self, db: AsyncSession, building_id: uuid.UUID, number: int) -> Floor | None:
        result = await db.execute(select(Floor).where(Floor.building_id == building_id, Floor.number == number))
        return result.scalar_one_or_none()


class ApartmentRepository:
    async def get_by_id(self, db: AsyncSession, apartment_id: uuid.UUID) -> Apartment | None:
        return await db.get(Apartment, apartment_id)

    async def get_by_id_with_floor(self, db: AsyncSession, apartment_id: uuid.UUID) -> Apartment | None:
        result = await db.execute(
            select(Apartment).options(selectinload(Apartment.floor)).where(Apartment.id == apartment_id)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> Apartment:
        apartment = Apartment(**data)
        db.add(apartment)
        await db.flush()
        await db.refresh(apartment)
        return apartment

    async def update(self, db: AsyncSession, apartment: Apartment, data: dict) -> Apartment:
        for key, value in data.items():
            setattr(apartment, key, value)
        await db.flush()
        await db.refresh(apartment)
        return apartment

    async def list_by_floor(self, db: AsyncSession, floor_id: uuid.UUID) -> list[Apartment]:
        result = await db.execute(select(Apartment).where(Apartment.floor_id == floor_id).order_by(Apartment.number))
        return list(result.scalars().all())

    async def list_by_building(self, db: AsyncSession, building_id: uuid.UUID) -> list[Apartment]:
        result = await db.execute(
            select(Apartment)
            .join(Floor)
            .where(Floor.building_id == building_id)
            .order_by(Floor.number.desc(), Apartment.number)
        )
        return list(result.scalars().all())

    async def list_filtered(
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
        query = select(Apartment).join(Floor)

        if rooms is not None:
            query = query.where(Apartment.rooms == rooms)
        if area_min is not None:
            query = query.where(Apartment.area >= area_min)
        if area_max is not None:
            query = query.where(Apartment.area <= area_max)
        if price_min is not None:
            query = query.where(Apartment.price >= price_min)
        if price_max is not None:
            query = query.where(Apartment.price <= price_max)
        if status is not None:
            query = query.where(Apartment.status == status)
        if floor_number is not None:
            query = query.where(Floor.number == floor_number)
        if building_id is not None:
            query = query.where(Floor.building_id == building_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        query = query.order_by(Floor.number.desc(), Apartment.number).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def get_statistics(self, db: AsyncSession, building_id: uuid.UUID) -> dict:
        rows = await db.execute(
            select(
                func.count(Apartment.id).label("total"),
                func.sum(Apartment.price).label("total_revenue"),
            )
            .join(Floor)
            .where(Floor.building_id == building_id)
        )
        total_row = rows.one()
        total = total_row.total or 0
        total_revenue = total_row.total_revenue or 0

        status_counts = {}
        for s in ApartmentStatus:
            row = await db.execute(
                select(func.count(Apartment.id))
                .join(Floor)
                .where(Floor.building_id == building_id, Apartment.status == s)
            )
            status_counts[s.value] = row.scalar_one()

        return {
            "total_apartments": total,
            "available": status_counts.get("available", 0),
            "reserved": status_counts.get("reserved", 0),
            "sold": status_counts.get("sold", 0),
            "blocked": status_counts.get("blocked", 0),
            "total_revenue": float(total_revenue or 0),
        }

    async def get_by_building_floor_and_number(
        self, db: AsyncSession, floor_id: uuid.UUID, number: str
    ) -> Apartment | None:
        result = await db.execute(select(Apartment).where(Apartment.floor_id == floor_id, Apartment.number == number))
        return result.scalar_one_or_none()


project_repo = ProjectRepository()
building_repo = BuildingRepository()
section_repo = SectionRepository()
floor_repo = FloorRepository()
apartment_repo = ApartmentRepository()
