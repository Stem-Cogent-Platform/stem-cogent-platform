"""Create PostgreSQL schema namespaces.

Revision ID: 0001
Revises:
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMAS = (
    "auth",
    "config",
    "pipeline",
    "intelligence",
    "delivery",
    "cil",
    "feedback",
    "billing",
    "audit",
)


def upgrade() -> None:
    for schema in SCHEMAS:
        op.execute(f'CREATE SCHEMA "{schema}"')


def downgrade() -> None:
    for schema in reversed(SCHEMAS):
        op.execute(f'DROP SCHEMA "{schema}"')
