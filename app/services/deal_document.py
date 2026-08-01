from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.core.exceptions import BadRequest, NotFound
from app.models.deal_document import DealDocument, DealDocumentType
from app.models.deal_timeline import DealEvent
from app.models.user import User
from app.repositories.deal_document import deal_document_repo
from app.services.deal import deal_service
from app.services.deal_timeline import timeline_service

MAX_DOCUMENT_SIZE_MB: int = 50
MAX_DOCUMENT_SIZE_BYTES = MAX_DOCUMENT_SIZE_MB * 1024 * 1024


class DocumentService:
    async def create(
        self,
        db: AsyncSession,
        actor: User,
        deal_id: uuid.UUID,
        document_type: DealDocumentType,
        title: str,
        file: UploadFile,
    ) -> DealDocument:
        deal = await deal_service.get_deal_for_write(db, actor, deal_id)

        content = await file.read()
        if len(content) > MAX_DOCUMENT_SIZE_BYTES:
            raise BadRequest(f"File exceeds the maximum size of {MAX_DOCUMENT_SIZE_MB} MB")

        original_name = Path(file.filename or "document").name
        extension = Path(original_name).suffix
        stored_name = f"{uuid.uuid4().hex}{extension}"
        deal_dir = Path(settings.UPLOAD_DIR) / "deals" / str(deal_id)
        deal_dir.mkdir(parents=True, exist_ok=True)
        target = deal_dir / stored_name
        target.write_bytes(content)

        document = await deal_document_repo.create(
            db,
            {
                "deal_id": deal_id,
                "document_type": document_type,
                "title": title,
                "file_name": original_name,
                "file_path": str(target),
                "file_size": len(content),
                "mime_type": file.content_type,
                "uploaded_by": actor.id,
            },
        )
        timeline_service.record(db, deal.id, DealEvent.DOCUMENT_ADDED, new_value=title, performed_by=actor.id)
        return document

    async def list(self, db: AsyncSession, actor: User, deal_id: uuid.UUID) -> list[DealDocument]:
        await deal_service.get_deal_for_read(db, actor, deal_id)
        return await deal_document_repo.list_by_deal(db, deal_id)

    async def delete(self, db: AsyncSession, actor: User, document_id: uuid.UUID) -> None:
        document = await self._get_document_or_404(db, document_id)
        deal = await deal_service.get_deal_for_write(db, actor, document.deal_id)
        stored = Path(document.file_path)
        if stored.exists():
            stored.unlink()
        await deal_document_repo.delete(db, document)
        timeline_service.record(
            db, deal.id, DealEvent.DOCUMENT_DELETED, old_value=document.title, performed_by=actor.id
        )

    async def _get_document_or_404(self, db: AsyncSession, document_id: uuid.UUID) -> DealDocument:
        document = await deal_document_repo.get_by_id(db, document_id)
        if not document:
            raise NotFound("Document not found")
        return document


document_service = DocumentService()
