"""Create tenant-isolated human intelligence review cases.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE feedback.review_cases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            submitted_by UUID NOT NULL,
            review_type VARCHAR(40) NOT NULL,
            signal_id UUID NOT NULL,
            entity_id UUID REFERENCES intelligence.entities(id),
            brief_id UUID,
            idempotency_key UUID NOT NULL,
            reason_code VARCHAR(60) NOT NULL,
            explanation TEXT,
            observed_values JSONB NOT NULL DEFAULT '{}'::JSONB,
            proposed_values JSONB NOT NULL DEFAULT '{}'::JSONB,
            status VARCHAR(25) NOT NULL DEFAULT 'OPEN',
            resolution JSONB,
            resolved_by UUID,
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT review_cases_idempotency_key
                UNIQUE (tenant_id, submitted_by, idempotency_key),
            CONSTRAINT review_cases_submitter_fkey
                FOREIGN KEY (tenant_id, submitted_by)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT review_cases_resolver_fkey
                FOREIGN KEY (tenant_id, resolved_by)
                REFERENCES auth.users (tenant_id, id),
            CONSTRAINT review_cases_brief_fkey
                FOREIGN KEY (tenant_id, brief_id)
                REFERENCES decision.briefs (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT review_cases_type_check CHECK (review_type IN (
                'SOURCE_VALIDATION', 'CLASSIFICATION', 'ENTITY_RESOLUTION',
                'DECISION_RELEVANCE'
            )),
            CONSTRAINT review_cases_status_check CHECK (status IN (
                'OPEN', 'IN_REVIEW', 'RESOLVED', 'REJECTED'
            )),
            CONSTRAINT review_cases_entity_subject_check CHECK (
                review_type <> 'ENTITY_RESOLUTION' OR entity_id IS NOT NULL
            ),
            CONSTRAINT review_cases_brief_subject_check CHECK (
                review_type <> 'DECISION_RELEVANCE' OR brief_id IS NOT NULL
            ),
            CONSTRAINT review_cases_observed_object_check
                CHECK (jsonb_typeof(observed_values) = 'object'),
            CONSTRAINT review_cases_proposed_object_check
                CHECK (jsonb_typeof(proposed_values) = 'object'),
            CONSTRAINT review_cases_resolution_object_check CHECK (
                resolution IS NULL OR jsonb_typeof(resolution) = 'object'
            ),
            CONSTRAINT review_cases_resolution_state_check CHECK (
                (status IN ('OPEN', 'IN_REVIEW') AND resolved_by IS NULL AND resolved_at IS NULL)
                OR (status IN ('RESOLVED', 'REJECTED') AND resolved_by IS NOT NULL
                    AND resolved_at IS NOT NULL AND resolution IS NOT NULL)
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_review_cases_tenant_queue
        ON feedback.review_cases (tenant_id, status, review_type, created_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_review_cases_signal
        ON feedback.review_cases (tenant_id, signal_id, created_at DESC)
        """
    )
    op.execute("ALTER TABLE feedback.review_cases ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_review_cases ON feedback.review_cases
        FOR ALL
        USING (tenant_id = {_CURRENT_TENANT})
        WITH CHECK (tenant_id = {_CURRENT_TENANT})
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE feedback.review_cases")
