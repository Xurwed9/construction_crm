import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.deal_activity import DealActivity
    from app.models.deal_document import DealDocument
    from app.models.deal_payment import DealPayment
    from app.models.deal_task import DealTask
    from app.models.deal_timeline import DealTimeline
    from app.models.lead import Lead
    from app.models.matrix import Apartment, Building, Floor, Project, Section
    from app.models.user import User


class DealStatus(str, enum.Enum):
    NEW = "new"
    CONSULTATION = "consultation"
    MEETING = "meeting"
    NEGOTIATION = "negotiation"
    RESERVED = "reserved"
    CONTRACT = "contract"
    INSTALLMENT = "installment"
    MORTGAGE = "mortgage"
    SOLD = "sold"
    CANCELLED = "cancelled"


class DealPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class DealPaymentType(str, enum.Enum):
    CASH = "cash"
    INSTALLMENT = "installment"
    MORTGAGE = "mortgage"
    MIXED = "mixed"


STATUS_TRANSITIONS: dict[DealStatus, set[DealStatus]] = {
    DealStatus.NEW: {DealStatus.CONSULTATION, DealStatus.MEETING, DealStatus.NEGOTIATION, DealStatus.CANCELLED},
    DealStatus.CONSULTATION: {DealStatus.NEW, DealStatus.MEETING, DealStatus.NEGOTIATION, DealStatus.CANCELLED},
    DealStatus.MEETING: {DealStatus.CONSULTATION, DealStatus.NEGOTIATION, DealStatus.RESERVED, DealStatus.CANCELLED},
    DealStatus.NEGOTIATION: {DealStatus.MEETING, DealStatus.CONSULTATION, DealStatus.RESERVED, DealStatus.CANCELLED},
    DealStatus.RESERVED: {DealStatus.NEGOTIATION, DealStatus.CONTRACT, DealStatus.CANCELLED},
    DealStatus.CONTRACT: {DealStatus.INSTALLMENT, DealStatus.MORTGAGE, DealStatus.RESERVED, DealStatus.CANCELLED},
    DealStatus.INSTALLMENT: {DealStatus.CONTRACT, DealStatus.MORTGAGE, DealStatus.CANCELLED},
    DealStatus.MORTGAGE: {DealStatus.CONTRACT, DealStatus.INSTALLMENT, DealStatus.CANCELLED},
    DealStatus.SOLD: set(),
    DealStatus.CANCELLED: {DealStatus.NEW},
}

ACTIVE_STATUSES: frozenset[DealStatus] = frozenset(
    {
        DealStatus.NEW,
        DealStatus.CONSULTATION,
        DealStatus.MEETING,
        DealStatus.NEGOTIATION,
        DealStatus.RESERVED,
        DealStatus.CONTRACT,
        DealStatus.INSTALLMENT,
        DealStatus.MORTGAGE,
    }
)

SELLABLE_STATUSES: frozenset[DealStatus] = frozenset(
    {
        DealStatus.RESERVED,
        DealStatus.CONTRACT,
        DealStatus.INSTALLMENT,
        DealStatus.MORTGAGE,
    }
)

PRE_RESERVATION_STATUSES: frozenset[DealStatus] = frozenset(
    {
        DealStatus.NEW,
        DealStatus.CONSULTATION,
        DealStatus.MEETING,
        DealStatus.NEGOTIATION,
    }
)

PRIORITY_WEIGHTS: dict[DealPriority, int] = {
    DealPriority.LOW: 1,
    DealPriority.MEDIUM: 2,
    DealPriority.HIGH: 3,
    DealPriority.URGENT: 4,
}


class Deal(Base):
    __tablename__ = "deals"

    __table_args__ = (
        Index(
            "uq_deals_active_apartment",
            "apartment_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL AND status NOT IN ('sold', 'cancelled')"),
            sqlite_where=text("deleted_at IS NULL AND status NOT IN ('sold', 'cancelled')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deal_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    building_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True
    )
    floor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("floors.id", ondelete="SET NULL"), nullable=True
    )
    apartment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apartments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[DealStatus] = mapped_column(
        Enum(DealStatus, values_callable=lambda x: [e.value for e in x]),
        default=DealStatus.NEW,
        nullable=False,
        index=True,
    )
    priority: Mapped[DealPriority] = mapped_column(
        Enum(DealPriority, values_callable=lambda x: [e.value for e in x]),
        default=DealPriority.MEDIUM,
        nullable=False,
    )
    payment_type: Mapped[DealPaymentType] = mapped_column(
        Enum(DealPaymentType, values_callable=lambda x: [e.value for e in x]),
        default=DealPaymentType.CASH,
        nullable=False,
    )
    reservation_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reservation_expired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    contract_number: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    discount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    paid_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    remaining_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    expected_close_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lead: Mapped["Lead | None"] = relationship("Lead", foreign_keys=[lead_id], lazy="selectin")
    client: Mapped["User | None"] = relationship("User", foreign_keys=[client_id], lazy="selectin")
    manager: Mapped["User | None"] = relationship("User", foreign_keys=[manager_id], lazy="selectin")
    project: Mapped["Project | None"] = relationship("Project", foreign_keys=[project_id], lazy="selectin")
    building: Mapped["Building | None"] = relationship("Building", foreign_keys=[building_id], lazy="selectin")
    section: Mapped["Section | None"] = relationship("Section", foreign_keys=[section_id], lazy="selectin")
    floor: Mapped["Floor | None"] = relationship("Floor", foreign_keys=[floor_id], lazy="selectin")
    apartment: Mapped["Apartment | None"] = relationship("Apartment", foreign_keys=[apartment_id], lazy="selectin")

    timeline: Mapped[list["DealTimeline"]] = relationship(
        "DealTimeline", back_populates="deal", lazy="raise", cascade="all, delete-orphan"
    )
    activities: Mapped[list["DealActivity"]] = relationship(
        "DealActivity", back_populates="deal", lazy="raise", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["DealTask"]] = relationship(
        "DealTask", back_populates="deal", lazy="raise", cascade="all, delete-orphan"
    )
    documents: Mapped[list["DealDocument"]] = relationship(
        "DealDocument", back_populates="deal", lazy="raise", cascade="all, delete-orphan"
    )
    payments: Mapped[list["DealPayment"]] = relationship(
        "DealPayment", back_populates="deal", lazy="raise", cascade="all, delete-orphan"
    )
