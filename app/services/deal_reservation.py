from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.matrix import Apartment, ApartmentStatus
from app.repositories.matrix import apartment_repo


class ReservationService:
    """Owns every mutation of the apartment matrix driven by a deal lifecycle."""

    async def hold(self, db: AsyncSession, apartment: Apartment, deal_id: uuid.UUID) -> Apartment:
        return await apartment_repo.update(db, apartment, {"status": ApartmentStatus.RESERVED, "deal_id": deal_id})

    async def release(self, db: AsyncSession, apartment: Apartment) -> Apartment:
        return await apartment_repo.update(db, apartment, {"status": ApartmentStatus.AVAILABLE, "deal_id": None})

    async def mark_sold(self, db: AsyncSession, apartment: Apartment, deal_id: uuid.UUID) -> Apartment:
        return await apartment_repo.update(db, apartment, {"status": ApartmentStatus.SOLD, "deal_id": deal_id})


reservation_service = ReservationService()
