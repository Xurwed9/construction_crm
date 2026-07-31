"""fix enum values to lowercase for projectstatus and apartmentstatus

Revision ID: 005
Revises: 004
Create Date: 2026-07-30

"""

from collections.abc import Sequence

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE projects ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE projectstatus RENAME TO projectstatus_old")
    op.execute("CREATE TYPE projectstatus AS ENUM('active', 'archived')")
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE projectstatus USING status::text::projectstatus")
    op.execute("ALTER TABLE projects ALTER COLUMN status SET DEFAULT 'active'")
    op.execute("DROP TYPE IF EXISTS projectstatus_old")

    op.execute("ALTER TABLE apartments ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE apartmentstatus RENAME TO apartmentstatus_old")
    op.execute("CREATE TYPE apartmentstatus AS ENUM('available', 'reserved', 'sold', 'blocked')")
    op.execute("ALTER TABLE apartments ALTER COLUMN status TYPE apartmentstatus USING status::text::apartmentstatus")
    op.execute("ALTER TABLE apartments ALTER COLUMN status SET DEFAULT 'available'")
    op.execute("DROP TYPE IF EXISTS apartmentstatus_old")


def downgrade() -> None:
    op.execute("ALTER TABLE projects ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE projectstatus RENAME TO projectstatus_old")
    op.execute("CREATE TYPE projectstatus AS ENUM('ACTIVE', 'ARCHIVED')")
    op.execute("ALTER TABLE projects ALTER COLUMN status TYPE projectstatus USING status::text::projectstatus")
    op.execute("ALTER TABLE projects ALTER COLUMN status SET DEFAULT 'ACTIVE'")
    op.execute("DROP TYPE IF EXISTS projectstatus_old")

    op.execute("ALTER TABLE apartments ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TYPE apartmentstatus RENAME TO apartmentstatus_old")
    op.execute("CREATE TYPE apartmentstatus AS ENUM('AVAILABLE', 'RESERVED', 'SOLD', 'BLOCKED')")
    op.execute("ALTER TABLE apartments ALTER COLUMN status TYPE apartmentstatus USING status::text::apartmentstatus")
    op.execute("ALTER TABLE apartments ALTER COLUMN status SET DEFAULT 'AVAILABLE'")
    op.execute("DROP TYPE IF EXISTS apartmentstatus_old")
