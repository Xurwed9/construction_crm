import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.user import User


class DealDocumentType(str, enum.Enum):
    PASSPORT = "passport"
    CONTRACT = "contract"
    RECEIPT = "receipt"
    INVOICE = "invoice"
    MORTGAGE = "mortgage"
    PHOTO = "photo"
    BLUEPRINT = "blueprint"
    PDF = "pdf"


class DealDocument(Base):
    __tablename__ = "deal_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_type: Mapped[DealDocumentType] = mapped_column(
        Enum(DealDocumentType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    deal: Mapped["Deal"] = relationship("Deal", back_populates="documents", lazy="raise")
    uploader: Mapped["User | None"] = relationship("User", foreign_keys=[uploaded_by], lazy="selectin")
