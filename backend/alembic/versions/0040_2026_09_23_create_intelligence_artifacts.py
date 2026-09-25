"""Create pipeline.intelligence_artifacts for the 3 core output engines.

Revision ID: 0040
Revises: 0039
Create Date: 2026-09-23
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE pipeline.intelligence_artifacts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            signal_id UUID NOT NULL,
            relevance_id UUID,
            artifact_type VARCHAR(30) NOT NULL,
            title VARCHAR(255) NOT NULL,
            payload JSONB NOT NULL,
            urgency VARCHAR(20) NOT NULL,
            is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
            synthesis_provider VARCHAR(30) NOT NULL DEFAULT 'deterministic',
            synthesis_model VARCHAR(60) NOT NULL DEFAULT 'artifact-synthesizer-v1',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT intelligence_artifacts_type_check CHECK (
                artifact_type IN (
                    'compliance_gap',
                    'competitive_battlecard',
                    'rail_stress'
                )
            ),
            CONSTRAINT intelligence_artifacts_urgency_check CHECK (
                urgency IN (
                    'low', 'moderate', 'high', 'critical',
                    'monitor', 'this_quarter', 'this_month', 'this_week', 'immediate'
                )
            ),
            CONSTRAINT intelligence_artifacts_payload_object_check CHECK (
                jsonb_typeof(payload) = 'object'
            ),
            CONSTRAINT uq_artifacts_tenant_signal_type
                UNIQUE (tenant_id, signal_id, artifact_type)
        );
        """
    )

    # Composite B-Tree for tenant-scoped filtered queries
    op.execute(
        """
        CREATE INDEX ix_artifacts_tenant_type_created
            ON pipeline.intelligence_artifacts (tenant_id, artifact_type, created_at DESC);
        """
    )

    # GIN index for JSONB payload querying
    op.execute(
        """
        CREATE INDEX ix_artifacts_payload_gin
            ON pipeline.intelligence_artifacts USING gin (payload);
        """
    )

    # Row Level Security — tenant isolation matching codebase patterns
    op.execute(
        "ALTER TABLE pipeline.intelligence_artifacts ENABLE ROW LEVEL SECURITY;"
    )
    op.execute(
        f"""
        CREATE POLICY intelligence_artifacts_tenant_isolation
            ON pipeline.intelligence_artifacts
            USING (
                tenant_id = {_CURRENT_TENANT}
                OR current_setting('app.system_admin', true) = 'true'
            );
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS intelligence_artifacts_tenant_isolation "
        "ON pipeline.intelligence_artifacts;"
    )
    op.execute("DROP TABLE IF EXISTS pipeline.intelligence_artifacts;")
