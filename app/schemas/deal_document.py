import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.deal_document import DealDocumentType


class DealDocumentCreate(BaseModel):
    document_type: DealDocumentType
    title: str = Field(..., min_length=1, max_length=255)


class DealDocumentRead(BaseModel):
    id: uuid.UUID
    deal_id: uuid.UUID
    document_type: DealDocumentType
    title: str
    file_name: str
    file_path: str
    file_size: int
    mime_type: str | None
    uploaded_by: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}
