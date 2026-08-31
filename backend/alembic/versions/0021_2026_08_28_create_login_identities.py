"""Create the pre-authentication identity index used by public sign-in.

Revision ID: 0021
Revises: 0020
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # This deliberately small table is not tenant-RLS protected: it is the
    # exact-match bridge from a normal email sign-in to the tenant context
    # that must be set before auth.users can be queried under forced RLS.
    op.execute(
        """
        CREATE TABLE auth.login_identities (
            email VARCHAR(320) PRIMARY KEY,
            tenant_id UUID NOT NULL,
            user_id UUID NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT login_identities_user_key UNIQUE (tenant_id, user_id),
            CONSTRAINT login_identities_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id)
                ON DELETE CASCADE,
            CONSTRAINT login_identities_email_normalised_check
                CHECK (email = LOWER(BTRIM(email)))
        )
        """
    )
    op.execute(
        """
        INSERT INTO auth.login_identities (email, tenant_id, user_id)
        SELECT LOWER(BTRIM(email)), tenant_id, id
        FROM auth.users
        ON CONFLICT (email) DO NOTHING
        """
    )
    op.execute("GRANT SELECT, INSERT ON auth.login_identities TO sc_app_runtime")
    op.execute(
        "REVOKE UPDATE, DELETE, TRUNCATE ON auth.login_identities FROM sc_app_runtime"
    )


def downgrade() -> None:
    op.execute("DROP TABLE auth.login_identities")
