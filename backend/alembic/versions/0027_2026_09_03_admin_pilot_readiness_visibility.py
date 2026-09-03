"""Allow system administrators to read pilot personalization readiness.

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_READINESS_TABLES = ("user_decision_lenses", "focus_areas")


def upgrade() -> None:
    # Internal readiness only counts these records. Restrict the additional
    # cross-tenant capability to SELECT; tenant users retain their existing
    # per-tenant ALL policies.
    for table in _READINESS_TABLES:
        op.execute(
            f"CREATE POLICY system_admin_read_{table} ON context.{table} "
            "FOR SELECT USING (current_setting('app.system_admin', true) = 'true')"
        )


def downgrade() -> None:
    for table in reversed(_READINESS_TABLES):
        op.execute(f"DROP POLICY system_admin_read_{table} ON context.{table}")
