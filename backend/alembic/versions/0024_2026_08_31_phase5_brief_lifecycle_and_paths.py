"""Add Phase 5 brief lifecycle, history, and bounded Decision Paths.

Revision ID: 0024
Revises: 0023
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def upgrade() -> None:
    op.execute("ALTER TABLE decision.briefs DROP CONSTRAINT briefs_status_check")
    op.execute(
        """
        ALTER TABLE decision.briefs
        ADD COLUMN first_published_at TIMESTAMPTZ,
        ADD COLUMN last_material_change_at TIMESTAMPTZ,
        ADD COLUMN resolved_at TIMESTAMPTZ,
        ADD COLUMN material_change_count INTEGER NOT NULL DEFAULT 0,
        ADD COLUMN gaps_summary TEXT,
        ADD COLUMN response_options JSONB,
        ADD COLUMN next_validation_steps TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
        ADD COLUMN guidance_status VARCHAR(20) NOT NULL DEFAULT 'NOT_GENERATED',
        ADD COLUMN guidance_generated_at TIMESTAMPTZ,
        ADD COLUMN guidance_rule_version VARCHAR(30),
        ADD CONSTRAINT briefs_status_check CHECK (
            brief_status IN ('OPEN','WATCHING','ESCALATED','ACTED_ON',
                             'DISMISSED','EXPIRED','RESOLVED')
        ),
        ADD CONSTRAINT briefs_material_change_count_check CHECK (material_change_count >= 0),
        ADD CONSTRAINT briefs_response_options_check CHECK (
            response_options IS NULL OR jsonb_typeof(response_options) = 'array'
        ),
        ADD CONSTRAINT briefs_guidance_status_check CHECK (
            guidance_status IN ('NOT_GENERATED','READY','INSUFFICIENT_CONTEXT','FAILED')
        )
        """
    )
    op.execute(
        """
        UPDATE decision.briefs
        SET first_published_at = created_at,
            last_material_change_at = created_at
        WHERE first_published_at IS NULL
        """
    )
    op.execute(
        "CREATE INDEX ix_briefs_material_change "
        "ON decision.briefs (tenant_id, last_material_change_at DESC)"
    )
    op.execute(
        """
        CREATE TABLE decision.brief_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            brief_id UUID NOT NULL,
            event_type VARCHAR(40) NOT NULL,
            event_metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT brief_events_brief_fkey
                FOREIGN KEY (tenant_id, brief_id)
                REFERENCES decision.briefs(tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT brief_events_type_check CHECK (
                event_type IN ('BRIEF_CREATED','BRIEF_UPDATED','STATUS_CHANGED',
                               'EVIDENCE_ADDED','RESOLVED')
            ),
            CONSTRAINT brief_events_metadata_check CHECK (jsonb_typeof(event_metadata) = 'object')
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_brief_events_brief_created "
        "ON decision.brief_events (tenant_id, brief_id, created_at)"
    )
    op.execute("ALTER TABLE decision.brief_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE decision.brief_events FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation_brief_events ON decision.brief_events "
        f"FOR ALL USING (tenant_id = {_CURRENT_TENANT}) "
        f"WITH CHECK (tenant_id = {_CURRENT_TENANT})"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON decision.brief_events TO sc_app_runtime"
    )
    op.execute(
        """
        UPDATE config.decision_rules
        SET output_contract = output_contract || CASE rule_code
          WHEN 'DR-REG-001' THEN '{"response_path_templates":["MONITOR","ESCALATE","COMMUNICATE"],"required_validation":["IMPLEMENTATION_DEADLINE","AFFECTED_PRODUCT_SCOPE","CURRENT_CONTROL_GAP"]}'::JSONB
          WHEN 'DR-INF-001' THEN '{"response_path_templates":["MONITOR","REROUTE","ESCALATE","COMMUNICATE"],"required_validation":["ALTERNATIVE_ROUTE_AVAILABILITY","CURRENT_FAILURE_RATE","AFFECTED_CUSTOMER_SEGMENT"]}'::JSONB
          WHEN 'DR-COMP-001' THEN '{"response_path_templates":["MONITOR","ESCALATE","COMMUNICATE"],"required_validation":["AFFECTED_CUSTOMER_SEGMENT","CURRENT_UNIT_ECONOMICS","COMPETITOR_OFFER_SCOPE"]}'::JSONB
          ELSE '{}'::JSONB
        END
        WHERE rule_code IN ('DR-REG-001','DR-INF-001','DR-COMP-001')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE config.decision_rules
        SET output_contract = output_contract - 'response_path_templates' - 'required_validation'
        WHERE rule_code IN ('DR-REG-001','DR-INF-001','DR-COMP-001')
        """
    )
    op.execute("DROP TABLE decision.brief_events")
    op.execute("DROP INDEX decision.ix_briefs_material_change")
    op.execute("ALTER TABLE decision.briefs DROP CONSTRAINT briefs_guidance_status_check")
    op.execute("ALTER TABLE decision.briefs DROP CONSTRAINT briefs_response_options_check")
    op.execute("ALTER TABLE decision.briefs DROP CONSTRAINT briefs_material_change_count_check")
    op.execute("ALTER TABLE decision.briefs DROP CONSTRAINT briefs_status_check")
    op.execute(
        """
        ALTER TABLE decision.briefs
        DROP COLUMN guidance_rule_version,
        DROP COLUMN guidance_generated_at,
        DROP COLUMN guidance_status,
        DROP COLUMN next_validation_steps,
        DROP COLUMN response_options,
        DROP COLUMN gaps_summary,
        DROP COLUMN material_change_count,
        DROP COLUMN resolved_at,
        DROP COLUMN last_material_change_at,
        DROP COLUMN first_published_at,
        ADD CONSTRAINT briefs_status_check CHECK (
            brief_status IN ('OPEN','WATCHING','ESCALATED','ACTED_ON','DISMISSED','EXPIRED')
        )
        """
    )
