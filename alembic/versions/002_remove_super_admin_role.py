"""remove super_admin role

Revision ID: 002
Revises: 001
Create Date: 2026-07-30
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM('admin', 'manager', 'client')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING CASE role::text "
        "WHEN 'SUPER_ADMIN' THEN 'admin'::userrole "
        "WHEN 'ADMIN' THEN 'admin'::userrole "
        "WHEN 'MANAGER' THEN 'manager'::userrole "
        "WHEN 'CLIENT' THEN 'client'::userrole "
        "END"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'client'")
    op.execute("DROP TYPE userrole_old")


def downgrade() -> None:
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM('SUPER_ADMIN', 'ADMIN', 'MANAGER', 'CLIENT')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE userrole "
        "USING CASE role::text "
        "WHEN 'admin' THEN 'ADMIN'::userrole "
        "WHEN 'manager' THEN 'MANAGER'::userrole "
        "WHEN 'client' THEN 'CLIENT'::userrole "
        "END"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'CLIENT'")
    op.execute("DROP TYPE userrole_old")
