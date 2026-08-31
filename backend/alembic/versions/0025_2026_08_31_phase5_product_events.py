"""Add privacy-aware Phase 5 product events.

Revision ID: 0025
Revises: 0024
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE feedback.product_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID,
            event_name VARCHAR(80) NOT NULL,
            object_type VARCHAR(40),
            object_id UUID,
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT product_events_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users(tenant_id, id) ON DELETE SET NULL (user_id),
            CONSTRAINT product_events_metadata_check CHECK (jsonb_typeof(metadata) = 'object'),
            CONSTRAINT product_events_name_check CHECK (event_name IN (
                'SESSION_STARTED','BRIEFING_VIEWED','BRIEF_OPENED','BRIEF_UPDATED_VIEWED',
                'EVIDENCE_PANEL_OPENED','CIL_OPENED','CIL_QUERY_SUBMITTED',
                'BRIEF_ACKNOWLEDGED','BRIEF_WATCHED','BRIEF_ESCALATED','BRIEF_ACTED_ON',
                'BRIEF_DISMISSED','WIDER_INTELLIGENCE_VIEWED','WATCHLIST_ITEM_VIEWED',
                'FOCUS_AREA_ADDED','FOCUS_AREA_UPDATED','SEARCH_PERFORMED','ALERT_OPENED',
                'DIGEST_OPENED','DECISION_PATHS_VIEWED'
            ))
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_product_events_tenant_time "
        "ON feedback.product_events (tenant_id, occurred_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_product_events_user_name_time "
        "ON feedback.product_events (tenant_id, user_id, event_name, occurred_at DESC)"
    )
    op.execute("ALTER TABLE feedback.product_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE feedback.product_events FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation_product_events ON feedback.product_events "
        f"FOR ALL USING (tenant_id = {_CURRENT_TENANT}) "
        f"WITH CHECK (tenant_id = {_CURRENT_TENANT})"
    )
    op.execute(
        "GRANT SELECT, INSERT ON feedback.product_events TO sc_app_runtime"
    )
    op.execute(
        "REVOKE UPDATE, DELETE, TRUNCATE ON feedback.product_events FROM sc_app_runtime"
    )


def downgrade() -> None:
    op.execute("DROP TABLE feedback.product_events")
