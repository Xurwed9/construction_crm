from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deal import Deal
from app.models.deal_payment import DealPayment


class DealPaymentRepository:
    async def get_by_id(self, db: AsyncSession, payment_id: uuid.UUID) -> DealPayment | None:
        return await db.get(DealPayment, payment_id)

    async def create(self, db: AsyncSession, data: dict) -> DealPayment:
        payment = DealPayment(**data)
        db.add(payment)
        await db.flush()
        return payment

    async def delete(self, db: AsyncSession, payment: DealPayment) -> None:
        await db.delete(payment)
        await db.flush()

    async def list_by_deal(self, db: AsyncSession, deal_id: uuid.UUID) -> list[DealPayment]:
        result = await db.execute(
            select(DealPayment).where(DealPayment.deal_id == deal_id).order_by(DealPayment.paid_at.desc())
        )
        return list(result.scalars().all())

    async def list_recent(
        self,
        db: AsyncSession,
        *,
        limit: int = 5,
        scope_manager_id: uuid.UUID | None = None,
        scope_client_id: uuid.UUID | None = None,
    ) -> list[DealPayment]:
        query = select(DealPayment).join(Deal, Deal.id == DealPayment.deal_id).where(Deal.deleted_at.is_(None))
        if scope_manager_id is not None:
            query = query.where(Deal.manager_id == scope_manager_id)
        if scope_client_id is not None:
            query = query.where(Deal.client_id == scope_client_id)
        result = await db.execute(query.order_by(DealPayment.paid_at.desc()).limit(limit))
        return list(result.scalars().all())


deal_payment_repo = DealPaymentRepository()
