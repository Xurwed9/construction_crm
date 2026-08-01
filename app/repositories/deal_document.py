from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deal_document import DealDocument


class DealDocumentRepository:
    async def get_by_id(self, db: AsyncSession, document_id: uuid.UUID) -> DealDocument | None:
        result = await db.execute(
            select(DealDocument).options(selectinload(DealDocument.uploader)).where(DealDocument.id == document_id)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict) -> DealDocument:
        document = DealDocument(**data)
        db.add(document)
        await db.flush()
        return document

    async def delete(self, db: AsyncSession, document: DealDocument) -> None:
        await db.delete(document)
        await db.flush()

    async def list_by_deal(self, db: AsyncSession, deal_id: uuid.UUID) -> list[DealDocument]:
        result = await db.execute(
            select(DealDocument)
            .options(selectinload(DealDocument.uploader))
            .where(DealDocument.deal_id == deal_id)
            .order_by(DealDocument.created_at.desc())
        )
        return list(result.scalars().all())


deal_document_repo = DealDocumentRepository()
