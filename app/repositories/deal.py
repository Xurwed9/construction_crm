from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.deal import (
    PRIORITY_WEIGHTS,
    Deal,
    DealPaymentType,
    DealPriority,
    DealStatus,
)
from app.models.lead import Lead
from app.models.matrix import Apartment, Building, Project
from app.models.user import User

PRIORITY_ORDER = case(
    *[(Deal.priority == p, w) for p, w in sorted(PRIORITY_WEIGHTS.items(), key=lambda x: x[1])],
    else_=0,
)

LOAD_OPTIONS = (
    selectinload(Deal.client),
    selectinload(Deal.manager),
    selectinload(Deal.lead),
    selectinload(Deal.apartment),
    selectinload(Deal.project),
    selectinload(Deal.building),
    selectinload(Deal.section),
    selectinload(Deal.floor),
)


def build_deal_filters(
    query,
    *,
    search: str | None = None,
    status: DealStatus | None = None,
    priority: DealPriority | None = None,
    manager_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    apartment_id: uuid.UUID | None = None,
    payment_type: DealPaymentType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    scope_manager_id: uuid.UUID | None = None,
    scope_client_id: uuid.UUID | None = None,
):
    if scope_client_id is not None:
        query = query.where(Deal.client_id == scope_client_id)
    if scope_manager_id is not None:
        query = query.where(Deal.manager_id == scope_manager_id)
    elif manager_id is not None:
        query = query.where(Deal.manager_id == manager_id)
    if status is not None:
        query = query.where(Deal.status == status)
    if priority is not None:
        query = query.where(Deal.priority == priority)
    if project_id is not None:
        query = query.where(Deal.project_id == project_id)
    if building_id is not None:
        query = query.where(Deal.building_id == building_id)
    if apartment_id is not None:
        query = query.where(Deal.apartment_id == apartment_id)
    if payment_type is not None:
        query = query.where(Deal.payment_type == payment_type)
    if date_from is not None:
        query = query.where(Deal.created_at >= date_from)
    if date_to is not None:
        query = query.where(Deal.created_at <= date_to)
    if search:
        pattern = f"%{search}%"
        client_exists = select(User.id).where(
            User.id == Deal.client_id,
            or_(
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
            ),
        )
        manager_exists = select(User.id).where(
            User.id == Deal.manager_id,
            or_(
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
                User.email.ilike(pattern),
                User.phone.ilike(pattern),
            ),
        )
        apartment_exists = select(Apartment.id).where(
            Apartment.id == Deal.apartment_id, Apartment.number.ilike(pattern)
        )
        project_exists = select(Project.id).where(Project.id == Deal.project_id, Project.name.ilike(pattern))
        building_exists = select(Building.id).where(Building.id == Deal.building_id, Building.name.ilike(pattern))
        lead_exists = select(Lead.id).where(
            Lead.id == Deal.lead_id,
            or_(Lead.full_name.ilike(pattern), Lead.phone.ilike(pattern), Lead.email.ilike(pattern)),
        )
        query = query.where(
            or_(
                Deal.deal_number.ilike(pattern),
                Deal.contract_number.ilike(pattern),
                client_exists.exists(),
                manager_exists.exists(),
                apartment_exists.exists(),
                project_exists.exists(),
                building_exists.exists(),
                lead_exists.exists(),
            )
        )
    return query


def apply_deal_sorting(query, sort: str):
    if sort == "oldest":
        return query.order_by(Deal.created_at.asc())
    if sort == "price":
        return query.order_by(Deal.final_price.desc().nulls_last(), Deal.created_at.desc())
    if sort == "remaining":
        return query.order_by(Deal.remaining_amount.desc().nulls_last(), Deal.created_at.desc())
    if sort == "created":
        return query.order_by(Deal.created_at.desc())
    if sort == "updated":
        return query.order_by(Deal.updated_at.desc())
    return query.order_by(Deal.created_at.desc())


class DealRepository:
    async def get_by_id(self, db: AsyncSession, deal_id: uuid.UUID) -> Deal | None:
        result = await db.execute(
            select(Deal).options(*LOAD_OPTIONS).where(Deal.id == deal_id, Deal.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_short_by_id(self, db: AsyncSession, deal_id: uuid.UUID) -> Deal | None:
        result = await db.execute(select(Deal).where(Deal.id == deal_id, Deal.deleted_at.is_(None)))
        return result.scalar_one_or_none()

    async def get_active_by_apartment(self, db: AsyncSession, apartment_id: uuid.UUID) -> Deal | None:
        result = await db.execute(
            select(Deal)
            .where(
                Deal.apartment_id == apartment_id,
                Deal.deleted_at.is_(None),
                Deal.status.not_in([DealStatus.SOLD, DealStatus.CANCELLED]),
            )
            .order_by(Deal.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_overdue_reservations(self, db: AsyncSession, now: datetime) -> list[Deal]:
        result = await db.execute(
            select(Deal)
            .options(selectinload(Deal.apartment))
            .where(
                Deal.status == DealStatus.RESERVED,
                Deal.reservation_expired.is_(False),
                Deal.reservation_until.is_not(None),
                Deal.reservation_until < now,
                Deal.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())

    async def list_reservation_expiring(
        self,
        db: AsyncSession,
        *,
        now: datetime,
        limit: int = 5,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> list[Deal]:
        query = select(Deal).where(
            Deal.deleted_at.is_(None),
            Deal.status == DealStatus.RESERVED,
            Deal.reservation_expired.is_(False),
            Deal.reservation_until.is_not(None),
            Deal.reservation_until <= now,
        )
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        result = await db.execute(query.options(*LOAD_OPTIONS).order_by(Deal.reservation_until.asc()).limit(limit))
        return list(result.scalars().all())

    async def count(
        self,
        db: AsyncSession,
        *,
        status: DealStatus | None = None,
        exclude_statuses: list[DealStatus] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> int:
        query = select(func.count(Deal.id)).where(Deal.deleted_at.is_(None))
        if status is not None:
            query = query.where(Deal.status == status)
        if exclude_statuses:
            query = query.where(Deal.status.not_in(exclude_statuses))
        if date_from is not None:
            query = query.where(Deal.created_at >= date_from)
        if date_to is not None:
            query = query.where(Deal.created_at <= date_to)
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        return (await db.execute(query)).scalar_one()

    async def get_revenue(
        self,
        db: AsyncSession,
        *,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> float:
        query = select(func.coalesce(func.sum(Deal.final_price), 0.0)).where(
            Deal.deleted_at.is_(None), Deal.status == DealStatus.SOLD
        )
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        return float((await db.execute(query)).scalar_one())

    async def get_top_managers(
        self,
        db: AsyncSession,
        *,
        limit: int = 5,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> list[dict]:
        sold_case = case((Deal.status == DealStatus.SOLD, 1), else_=0)
        revenue_case = case((Deal.status == DealStatus.SOLD, Deal.final_price), else_=0.0)
        manager_name_expr = (User.first_name + " " + User.last_name).label("manager_name")
        query = (
            select(
                Deal.manager_id.label("manager_id"),
                manager_name_expr,
                func.count(Deal.id).label("total_deals"),
                func.sum(sold_case).label("sold_deals"),
                func.coalesce(func.sum(revenue_case), 0.0).label("revenue"),
            )
            .outerjoin(User, User.id == Deal.manager_id)
            .where(Deal.deleted_at.is_(None))
        )
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        query = query.group_by(Deal.manager_id, manager_name_expr).order_by(desc("revenue")).limit(limit)
        rows = (await db.execute(query)).all()
        return [
            {
                "manager_id": row.manager_id,
                "manager_name": row.manager_name,
                "total_deals": row.total_deals,
                "sold_deals": row.sold_deals,
                "revenue": float(row.revenue),
            }
            for row in rows
        ]

    async def get_avg_closing_time_days(
        self,
        db: AsyncSession,
        *,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> float | None:
        if settings.is_sqlite:
            seconds_expr = func.avg(func.strftime("%s", Deal.closed_at) - func.strftime("%s", Deal.created_at))
        else:
            seconds_expr = func.avg(func.extract("epoch", Deal.closed_at - Deal.created_at))
        query = select(seconds_expr).where(
            Deal.deleted_at.is_(None), Deal.status == DealStatus.SOLD, Deal.closed_at.is_not(None)
        )
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        seconds = (await db.execute(query)).scalar_one()
        if seconds is None:
            return None
        return round(float(seconds) / 86400.0, 2)

    async def create(self, db: AsyncSession, data: dict) -> Deal:
        deal = Deal(**data)
        db.add(deal)
        await db.flush()
        return deal

    async def update(self, db: AsyncSession, deal: Deal, data: dict) -> Deal:
        for key, value in data.items():
            setattr(deal, key, value)
        await db.flush()
        return deal

    async def soft_delete(self, db: AsyncSession, deal: Deal) -> Deal:
        deal.deleted_at = func.now()
        await db.flush()
        return deal

    async def list(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        status: DealStatus | None = None,
        priority: DealPriority | None = None,
        manager_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        building_id: uuid.UUID | None = None,
        apartment_id: uuid.UUID | None = None,
        payment_type: DealPaymentType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: str = "newest",
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> tuple[list[Deal], int]:
        query = select(Deal).where(Deal.deleted_at.is_(None))
        query = build_deal_filters(
            query,
            search=search,
            status=status,
            priority=priority,
            manager_id=manager_id,
            project_id=project_id,
            building_id=building_id,
            apartment_id=apartment_id,
            payment_type=payment_type,
            date_from=date_from,
            date_to=date_to,
            scope_manager_id=scope_manager_id,
            scope_client_id=scope_client_id,
        )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        query = apply_deal_sorting(query, sort)
        query = query.options(*LOAD_OPTIONS)
        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total


deal_repo = DealRepository()
