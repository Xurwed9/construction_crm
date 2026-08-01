"""create deal management tables

Revision ID: 007
Revises: 006
Create Date: 2026-08-01

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "deals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deal_number", sa.String(50), nullable=True),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("manager_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("building_id", sa.UUID(), nullable=True),
        sa.Column("section_id", sa.UUID(), nullable=True),
        sa.Column("floor_id", sa.UUID(), nullable=True),
        sa.Column("apartment_id", sa.UUID(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "new",
                "consultation",
                "meeting",
                "negotiation",
                "reserved",
                "contract",
                "installment",
                "mortgage",
                "sold",
                "cancelled",
                name="dealstatus",
            ),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "priority",
            sa.Enum("low", "medium", "high", "urgent", name="dealpriority"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "payment_type",
            sa.Enum("cash", "installment", "mortgage", "mixed", name="dealpaymenttype"),
            nullable=False,
            server_default="cash",
        ),
        sa.Column("reservation_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reservation_expired", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("contract_number", sa.String(50), nullable=True),
        sa.Column("price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("discount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("final_price", sa.Float(), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("remaining_amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("expected_close_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["apartment_id"], ["apartments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["client_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_deals_status", "deals", ["status"])
    op.create_index("ix_deals_deal_number", "deals", ["deal_number"])
    op.create_index("ix_deals_manager_id", "deals", ["manager_id"])
    op.create_index("ix_deals_apartment_id", "deals", ["apartment_id"])
    op.create_index("ix_deals_client_id", "deals", ["client_id"])
    op.create_index("ix_deals_lead_id", "deals", ["lead_id"])
    op.create_index("ix_deals_contract_number", "deals", ["contract_number"])
    op.create_index("ix_deals_reservation_until", "deals", ["reservation_until"])
    op.create_index(
        "uq_deals_active_apartment",
        "deals",
        ["apartment_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND status NOT IN ('sold', 'cancelled')"),
    )

    op.create_table(
        "deal_timelines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deal_id", sa.UUID(), nullable=False),
        sa.Column("event", sa.String(100), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("performed_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_deal_timelines_deal_id", "deal_timelines", ["deal_id"])
    op.create_index("ix_deal_timelines_event", "deal_timelines", ["event"])
    op.create_index("ix_deal_timelines_performed_by", "deal_timelines", ["performed_by"])
    op.create_index("ix_deal_timelines_created_at", "deal_timelines", ["created_at"])

    op.create_table(
        "deal_activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deal_id", sa.UUID(), nullable=False),
        sa.Column(
            "activity_type",
            sa.Enum(
                "call",
                "meeting",
                "telegram",
                "whatsapp",
                "email",
                "sms",
                "internal_note",
                "public_note",
                "task",
                "reminder",
                name="dealactivitytype",
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("performed_by", sa.UUID(), nullable=True),
        sa.Column("performed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_deal_activities_deal_id", "deal_activities", ["deal_id"])
    op.create_index("ix_deal_activities_activity_type", "deal_activities", ["activity_type"])
    op.create_index("ix_deal_activities_performed_by", "deal_activities", ["performed_by"])
    op.create_index("ix_deal_activities_scheduled_at", "deal_activities", ["scheduled_at"])

    op.create_table(
        "deal_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deal_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "priority",
            sa.Enum("low", "medium", "high", "urgent", name="taskpriority"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["assigned_to"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_deal_tasks_deal_id", "deal_tasks", ["deal_id"])
    op.create_index("ix_deal_tasks_deadline", "deal_tasks", ["deadline"])
    op.create_index("ix_deal_tasks_completed", "deal_tasks", ["completed"])
    op.create_index("ix_deal_tasks_assigned_to", "deal_tasks", ["assigned_to"])

    op.create_table(
        "deal_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deal_id", sa.UUID(), nullable=False),
        sa.Column(
            "document_type",
            sa.Enum(
                "passport",
                "contract",
                "receipt",
                "invoice",
                "mortgage",
                "photo",
                "blueprint",
                "pdf",
                name="dealdocumenttype",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_deal_documents_deal_id", "deal_documents", ["deal_id"])
    op.create_index("ix_deal_documents_document_type", "deal_documents", ["document_type"])

    op.create_table(
        "deal_payments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("deal_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column(
            "payment_method",
            sa.Enum("cash", "transfer", "card", "bank", "other", name="dealpaymentmethod"),
            nullable=False,
            server_default="cash",
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_deal_payments_deal_id", "deal_payments", ["deal_id"])
    op.create_index("ix_deal_payments_paid_at", "deal_payments", ["paid_at"])


def downgrade() -> None:
    op.drop_table("deal_payments")
    op.drop_table("deal_documents")
    op.drop_table("deal_tasks")
    op.drop_table("deal_activities")
    op.drop_table("deal_timelines")
    op.drop_table("deals")
    op.execute("DROP TYPE IF EXISTS dealpaymentmethod")
    op.execute("DROP TYPE IF EXISTS dealdocumenttype")
    op.execute("DROP TYPE IF EXISTS taskpriority")
    op.execute("DROP TYPE IF EXISTS dealactivitytype")
    op.execute("DROP TYPE IF EXISTS dealpaymenttype")
    op.execute("DROP TYPE IF EXISTS dealpriority")
    op.execute("DROP TYPE IF EXISTS dealstatus")
