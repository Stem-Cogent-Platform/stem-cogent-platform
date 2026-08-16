"""Create the Stem Cogent v2 schema namespaces.

Revision ID: 0001
Revises: None
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA_NAMES: tuple[str, ...] = (
    "auth",
    "config",
    "pipeline",
    "intelligence",
    "context",
    "decision",
    "delivery",
    "cil",
    "feedback",
    "billing",
    "audit",
)


def upgrade() -> None:
    for schema_name in SCHEMA_NAMES:
        op.execute(sa.schema.CreateSchema(schema_name))


def downgrade() -> None:
    for schema_name in reversed(SCHEMA_NAMES):
        op.execute(sa.schema.DropSchema(schema_name))
