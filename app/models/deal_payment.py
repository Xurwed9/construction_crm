import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.deal import Deal


class DealPaymentMethod(str, enum.Enum):
    CASH = "cash"
    TRANSFER = "transfer"
    CARD = "card"
    BANK = "bank"
    OTHER = "other"


class DealPayment(Base):
    __tablename__ = "deal_payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    payment_method: Mapped[DealPaymentMethod] = mapped_column(
        Enum(DealPaymentMethod, values_callable=lambda x: [e.value for e in x]),
        default=DealPaymentMethod.CASH,
        nullable=False,
    )
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    deal: Mapped["Deal"] = relationship("Deal", back_populates="payments", lazy="raise")
