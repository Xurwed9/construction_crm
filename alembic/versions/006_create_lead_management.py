"""create lead management tables

Revision ID: 006
Revises: 005
Create Date: 2026-07-31

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("full_name", sa.String(201), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("budget", sa.Float(), nullable=True),
        sa.Column(
            "priority",
            sa.Enum("low", "medium", "high", "urgent", name="leadpriority"),
            nullable=False,
            server_default="medium",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "new",
                "first_call",
                "consultation",
                "office_visit",
                "presentation",
                "decision",
                "reservation",
                "contract",
                "payment",
                "completed",
                "lost",
                name="leadstatus",
            ),
            nullable=False,
            server_default="new",
        ),
        sa.Column("lead_source", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assigned_manager_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("building_id", sa.UUID(), nullable=True),
        sa.Column("apartment_id", sa.UUID(), nullable=True),
        sa.Column("next_meeting_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["apartment_id"], ["apartments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_manager_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_leads_phone", "leads", ["phone"])
    op.create_index("ix_leads_email", "leads", ["email"])
    op.create_index("ix_leads_full_name", "leads", ["full_name"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_assigned_manager_id", "leads", ["assigned_manager_id"])

    op.create_table(
        "lead_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_lead_notes_lead_id", "lead_notes", ["lead_id"])

    op.create_table(
        "lead_timelines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("lead_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_lead_timelines_lead_id", "lead_timelines", ["lead_id"])


def downgrade() -> None:
    op.drop_table("lead_timelines")
    op.drop_table("lead_notes")
    op.drop_table("leads")
    op.execute("DROP TYPE IF EXISTS leadstatus")
    op.execute("DROP TYPE IF EXISTS leadpriority")
