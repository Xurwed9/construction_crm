"""create apartment matrix tables

Revision ID: 004
Revises: 003
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("address", sa.String(500), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "ARCHIVED", name="projectstatus"),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "buildings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("number_of_sections", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("floors_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "sections",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("building_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "floors",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("building_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["building_id"], ["buildings.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "apartments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("floor_id", sa.UUID(), nullable=False),
        sa.Column("section_id", sa.UUID(), nullable=True),
        sa.Column("number", sa.String(50), nullable=False),
        sa.Column("rooms", sa.Integer(), nullable=False),
        sa.Column("area", sa.Float(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default=sa.text("'USD'")),
        sa.Column(
            "status",
            sa.Enum("AVAILABLE", "RESERVED", "SOLD", "BLOCKED", name="apartmentstatus"),
            nullable=False,
            server_default="AVAILABLE",
        ),
        sa.Column("direction", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deal_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["floor_id"], ["floors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="SET NULL"),
    )


def downgrade() -> None:
    op.drop_table("apartments")
    op.drop_table("floors")
    op.drop_table("sections")
    op.drop_table("buildings")
    op.drop_table("projects")
    op.execute("DROP TYPE projectstatus")
    op.execute("DROP TYPE apartmentstatus")
