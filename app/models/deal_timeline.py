import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.deal import Deal
    from app.models.user import User


class DealEvent:
    LEAD_CONVERTED = "lead_converted"
    DEAL_CREATED = "deal_created"
    DEAL_UPDATED = "deal_updated"
    DEAL_DELETED = "deal_deleted"
    MANAGER_CHANGED = "manager_changed"
    APARTMENT_CHANGED = "apartment_changed"
    RESERVATION = "reservation"
    RESERVATION_EXPIRED = "reservation_expired"
    PAYMENT_ADDED = "payment_added"
    DISCOUNT_UPDATED = "discount_updated"
    STATUS_CHANGED = "status_changed"
    CONTRACT_CREATED = "contract_created"
    DEAL_CLOSED = "deal_closed"
    DEAL_CANCELLED = "deal_cancelled"
    DEAL_RESTORED = "deal_restored"
    ACTIVITY_ADDED = "activity_added"
    ACTIVITY_UPDATED = "activity_updated"
    ACTIVITY_DELETED = "activity_deleted"
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_DELETED = "task_deleted"
    DOCUMENT_ADDED = "document_added"
    DOCUMENT_DELETED = "document_deleted"


class DealTimeline(Base):
    __tablename__ = "deal_timelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    deal: Mapped["Deal"] = relationship("Deal", back_populates="timeline", lazy="raise")
    actor: Mapped["User | None"] = relationship("User", foreign_keys=[performed_by], lazy="selectin")
