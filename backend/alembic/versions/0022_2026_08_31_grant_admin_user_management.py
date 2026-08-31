"""Grant tenant administrators the documented user-management permission.

Revision ID: 0022
Revises: 0021
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE auth.roles
        SET permissions = array_append(permissions, 'MANAGE_USERS')
        WHERE role_code = 'ADMIN'
          AND NOT ('MANAGE_USERS' = ANY(permissions))
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE auth.roles
        SET permissions = array_remove(permissions, 'MANAGE_USERS')
        WHERE role_code = 'ADMIN'
        """
    )
