"""Create agent_sessions and agent_messages for Step 5 Decision Workspace.

Revision ID: 0041
Revises: 0040
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def upgrade() -> None:
    # 1. Create pipeline.agent_sessions with dual organization_id and tenant_id alignment
    op.execute(
        """
        CREATE TABLE pipeline.agent_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            tenant_id UUID GENERATED ALWAYS AS (organization_id) STORED,
            user_id UUID NOT NULL
                REFERENCES auth.users(id) ON DELETE CASCADE,
            title VARCHAR(255) NOT NULL DEFAULT 'Strategic Investigation',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    # 2. Composite indexes on agent_sessions for organization_id and tenant_id lookups
    op.execute(
        """
        CREATE INDEX ix_agent_sessions_org_user_updated
            ON pipeline.agent_sessions (organization_id, user_id, updated_at DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX ix_agent_sessions_tenant_user_updated
            ON pipeline.agent_sessions (tenant_id, user_id, updated_at DESC);
        """
    )

    # 3. Create pipeline.agent_messages with dual organization_id and tenant_id alignment
    op.execute(
        """
        CREATE TABLE pipeline.agent_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL
                REFERENCES pipeline.agent_sessions(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            tenant_id UUID GENERATED ALWAYS AS (organization_id) STORED,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            tool_provenance JSONB NULL,
            cited_artifact_ids UUID[] NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT agent_messages_role_check CHECK (
                role IN ('user', 'assistant', 'system')
            ),
            CONSTRAINT agent_messages_tool_provenance_check CHECK (
                tool_provenance IS NULL OR jsonb_typeof(tool_provenance) = 'object'
            )
        );
        """
    )

    # 4. Composite index on agent_messages for session chronological retrieval
    op.execute(
        """
        CREATE INDEX ix_agent_messages_session_created
            ON pipeline.agent_messages (session_id, created_at ASC);
        """
    )

    # 5. GIN index on cited_artifact_ids for reverse artifact citation queries
    op.execute(
        """
        CREATE INDEX ix_agent_messages_cited_artifacts
            ON pipeline.agent_messages USING gin (cited_artifact_ids)
            WHERE cited_artifact_ids IS NOT NULL;
        """
    )

    # 6. Row Level Security on pipeline.agent_sessions (supporting both organization_id and tenant_id)
    op.execute("ALTER TABLE pipeline.agent_sessions ENABLE ROW LEVEL SECURITY;")
    op.execute(
        f"""
        CREATE POLICY agent_sessions_tenant_isolation
            ON pipeline.agent_sessions
            USING (
                organization_id = {_CURRENT_TENANT}
                OR tenant_id = {_CURRENT_TENANT}
                OR current_setting('app.system_admin', true) = 'true'
            );
        """
    )

    # 7. Row Level Security on pipeline.agent_messages (supporting both organization_id and tenant_id)
    op.execute("ALTER TABLE pipeline.agent_messages ENABLE ROW LEVEL SECURITY;")
    op.execute(
        f"""
        CREATE POLICY agent_messages_tenant_isolation
            ON pipeline.agent_messages
            USING (
                organization_id = {_CURRENT_TENANT}
                OR tenant_id = {_CURRENT_TENANT}
                OR current_setting('app.system_admin', true) = 'true'
            );
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS agent_messages_tenant_isolation ON pipeline.agent_messages;"
    )
    op.execute(
        "DROP POLICY IF EXISTS agent_sessions_tenant_isolation ON pipeline.agent_sessions;"
    )
    op.execute("DROP TABLE IF EXISTS pipeline.agent_messages;")
    op.execute("DROP TABLE IF EXISTS pipeline.agent_sessions;")
