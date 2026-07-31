import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import User


class LeadStatus(str, enum.Enum):
    NEW = "new"
    FIRST_CALL = "first_call"
    CONSULTATION = "consultation"
    OFFICE_VISIT = "office_visit"
    PRESENTATION = "presentation"
    DECISION = "decision"
    RESERVATION = "reservation"
    CONTRACT = "contract"
    PAYMENT = "payment"
    COMPLETED = "completed"
    LOST = "lost"


class LeadPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(201), nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[LeadPriority] = mapped_column(
        Enum(LeadPriority, values_callable=lambda x: [e.value for e in x]),
        default=LeadPriority.MEDIUM,
        nullable=False,
    )
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, values_callable=lambda x: [e.value for e in x]),
        default=LeadStatus.NEW,
        nullable=False,
        index=True,
    )
    lead_source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    building_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buildings.id", ondelete="SET NULL"), nullable=True
    )
    apartment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("apartments.id", ondelete="SET NULL"), nullable=True
    )
    next_meeting_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    assigned_manager: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_manager_id], lazy="selectin")
    notes_rel: Mapped[list["LeadNote"]] = relationship(
        "LeadNote", back_populates="lead", lazy="raise", cascade="all, delete-orphan"
    )
    timeline: Mapped[list["LeadTimeline"]] = relationship(
        "LeadTimeline", back_populates="lead", lazy="raise", cascade="all, delete-orphan"
    )


class LeadNote(Base):
    __tablename__ = "lead_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    lead: Mapped["Lead"] = relationship("Lead", back_populates="notes_rel", lazy="raise")


class LeadTimeline(Base):
    __tablename__ = "lead_timelines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship("Lead", back_populates="timeline", lazy="raise")


STATUS_TRANSITIONS: dict[LeadStatus, set[LeadStatus]] = {
    LeadStatus.NEW: {LeadStatus.FIRST_CALL, LeadStatus.LOST},
    LeadStatus.FIRST_CALL: {LeadStatus.CONSULTATION, LeadStatus.NEW, LeadStatus.LOST},
    LeadStatus.CONSULTATION: {LeadStatus.OFFICE_VISIT, LeadStatus.FIRST_CALL, LeadStatus.LOST},
    LeadStatus.OFFICE_VISIT: {LeadStatus.PRESENTATION, LeadStatus.CONSULTATION, LeadStatus.LOST},
    LeadStatus.PRESENTATION: {LeadStatus.DECISION, LeadStatus.OFFICE_VISIT, LeadStatus.LOST},
    LeadStatus.DECISION: {LeadStatus.RESERVATION, LeadStatus.PRESENTATION, LeadStatus.LOST},
    LeadStatus.RESERVATION: {LeadStatus.CONTRACT, LeadStatus.DECISION, LeadStatus.LOST},
    LeadStatus.CONTRACT: {LeadStatus.PAYMENT, LeadStatus.RESERVATION, LeadStatus.LOST},
    LeadStatus.PAYMENT: {LeadStatus.COMPLETED, LeadStatus.CONTRACT, LeadStatus.LOST},
    LeadStatus.COMPLETED: set(),
    LeadStatus.LOST: {LeadStatus.NEW},
}

PRIORITY_WEIGHTS: dict[LeadPriority, int] = {
    LeadPriority.LOW: 1,
    LeadPriority.MEDIUM: 2,
    LeadPriority.HIGH: 3,
    LeadPriority.URGENT: 4,
}
