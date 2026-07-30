"""add super_admin role to userrole enum

Revision ID: 003
Revises: 002
Create Date: 2026-07-30

"""

from collections.abc import Sequence

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM('super_admin', 'admin', 'manager', 'client')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING CASE role::text "
        "WHEN 'admin' THEN 'admin'::userrole "
        "WHEN 'manager' THEN 'manager'::userrole "
        "WHEN 'client' THEN 'client'::userrole "
        "END"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'client'")
    op.execute("DROP TYPE userrole_old")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM('admin', 'manager', 'client')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING CASE role::text "
        "WHEN 'super_admin' THEN 'admin'::userrole "
        "WHEN 'admin' THEN 'admin'::userrole "
        "WHEN 'manager' THEN 'manager'::userrole "
        "WHEN 'client' THEN 'client'::userrole "
        "END"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'client'")
    op.execute("DROP TYPE userrole_old")
