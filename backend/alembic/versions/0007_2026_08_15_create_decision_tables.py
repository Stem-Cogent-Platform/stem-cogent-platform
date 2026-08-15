"""Create v2 tenant decision-assessment and brief tables.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"
_DECISION_TABLES = ("assessments", "briefs", "actions")


def _add_global_output_evidence_key() -> None:
    op.execute(
        """
        ALTER TABLE intelligence.global_outputs
        ADD CONSTRAINT global_outputs_id_signal_key UNIQUE (id, signal_id)
        """
    )


def _create_assessments() -> None:
    op.execute(
        """
        CREATE TABLE decision.assessments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            global_output_id UUID NOT NULL,
            signal_id UUID NOT NULL,
            company_context_version INTEGER NOT NULL,
            relevance_score NUMERIC(4,3) NOT NULL,
            relevance_band VARCHAR(20) NOT NULL,
            matched_object_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            exposure_types TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            stakes_types TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            decision_required BOOLEAN NOT NULL DEFAULT FALSE,
            decision_type VARCHAR(80),
            owner_role_codes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            decision_window TIMESTAMPTZ,
            quantification_status VARCHAR(20) NOT NULL
                DEFAULT 'NOT_AVAILABLE',
            quantitative_context JSONB,
            rationale JSONB NOT NULL,
            uncertainty_codes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            rule_version VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT assessments_tenant_id_id_key UNIQUE (tenant_id, id),
            CONSTRAINT assessments_id_signal_key UNIQUE (id, signal_id),
            CONSTRAINT assessments_idempotency_key UNIQUE (
                tenant_id,
                global_output_id,
                company_context_version
            ),
            CONSTRAINT assessments_global_output_signal_fkey
                FOREIGN KEY (global_output_id, signal_id)
                REFERENCES intelligence.global_outputs (id, signal_id)
                ON DELETE CASCADE,
            CONSTRAINT assessments_context_version_check
                CHECK (company_context_version >= 1),
            CONSTRAINT assessments_relevance_score_check
                CHECK (relevance_score BETWEEN 0 AND 1),
            CONSTRAINT assessments_quantitative_context_object_check CHECK (
                quantitative_context IS NULL
                OR jsonb_typeof(quantitative_context) = 'object'
            ),
            CONSTRAINT assessments_rationale_object_check
                CHECK (jsonb_typeof(rationale) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_assessments_tenant_relevance
            ON decision.assessments (
                tenant_id,
                decision_required,
                relevance_score DESC,
                created_at DESC
            )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_assessments_signal
            ON decision.assessments (signal_id, tenant_id)
        """
    )


def _create_briefs() -> None:
    op.execute(
        """
        CREATE TABLE decision.briefs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID,
            assessment_id UUID NOT NULL,
            signal_id UUID NOT NULL,
            lens_version INTEGER,
            personal_priority_score NUMERIC(4,3),
            what_changed TEXT NOT NULL,
            why_it_matters TEXT,
            exposure_summary TEXT,
            stakes_summary TEXT,
            decision_prompt TEXT,
            owner_roles TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            decision_window TIMESTAMPTZ,
            uncertainties TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            evidence_signal_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            brief_status VARCHAR(30) NOT NULL DEFAULT 'OPEN',
            synthesis_provider VARCHAR(50),
            synthesis_model VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT briefs_tenant_id_id_key UNIQUE (tenant_id, id),
            CONSTRAINT briefs_idempotency_key UNIQUE NULLS NOT DISTINCT (
                assessment_id,
                user_id,
                lens_version
            ),
            CONSTRAINT briefs_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT briefs_tenant_assessment_fkey
                FOREIGN KEY (tenant_id, assessment_id)
                REFERENCES decision.assessments (tenant_id, id)
                ON DELETE CASCADE,
            CONSTRAINT briefs_assessment_signal_fkey
                FOREIGN KEY (assessment_id, signal_id)
                REFERENCES decision.assessments (id, signal_id)
                ON DELETE CASCADE,
            CONSTRAINT briefs_user_lens_pair_check CHECK (
                (user_id IS NULL AND lens_version IS NULL)
                OR (user_id IS NOT NULL AND lens_version IS NOT NULL)
            ),
            CONSTRAINT briefs_lens_version_check
                CHECK (lens_version IS NULL OR lens_version >= 1),
            CONSTRAINT briefs_personal_priority_score_check
                CHECK (personal_priority_score BETWEEN 0 AND 1),
            CONSTRAINT briefs_status_check CHECK (
                brief_status IN (
                    'OPEN',
                    'WATCHING',
                    'ESCALATED',
                    'ACTED_ON',
                    'DISMISSED',
                    'EXPIRED'
                )
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_briefs_user_priority
            ON decision.briefs (
                tenant_id,
                user_id,
                personal_priority_score DESC,
                created_at DESC
            )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_briefs_company
            ON decision.briefs (tenant_id, created_at DESC)
            WHERE user_id IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ix_briefs_open_decision_window
            ON decision.briefs (tenant_id, decision_window, created_at DESC)
            WHERE brief_status IN ('OPEN', 'WATCHING', 'ESCALATED')
        """
    )


def _create_actions() -> None:
    op.execute(
        """
        CREATE TABLE decision.actions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            brief_id UUID NOT NULL,
            user_id UUID NOT NULL,
            action_type VARCHAR(30) NOT NULL,
            reason_code VARCHAR(50),
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT actions_tenant_brief_fkey
                FOREIGN KEY (tenant_id, brief_id)
                REFERENCES decision.briefs (tenant_id, id)
                ON DELETE CASCADE,
            CONSTRAINT actions_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id),
            CONSTRAINT actions_type_check CHECK (
                action_type IN (
                    'ACKNOWLEDGED',
                    'WATCHING',
                    'ESCALATED',
                    'ACTED_ON',
                    'DISMISSED'
                )
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_actions_brief_created
            ON decision.actions (tenant_id, brief_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_actions_user_created
            ON decision.actions (tenant_id, user_id, created_at DESC)
        """
    )


def _enable_tenant_rls() -> None:
    for table_name in _DECISION_TABLES:
        op.execute(f"ALTER TABLE decision.{table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table_name}
            ON decision.{table_name}
            FOR ALL
            USING (tenant_id = {_CURRENT_TENANT})
            WITH CHECK (tenant_id = {_CURRENT_TENANT})
            """
        )


def upgrade() -> None:
    _add_global_output_evidence_key()
    _create_assessments()
    _create_briefs()
    _create_actions()
    _enable_tenant_rls()


def downgrade() -> None:
    op.execute("DROP TABLE decision.actions")
    op.execute("DROP TABLE decision.briefs")
    op.execute("DROP TABLE decision.assessments")
    op.execute(
        """
        ALTER TABLE intelligence.global_outputs
        DROP CONSTRAINT global_outputs_id_signal_key
        """
    )
