"""Add durable personalisation state and activation quality diagnostics.

Revision ID: 0029
Revises: 0028
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE pilot.engagements DROP CONSTRAINT pilot_engagements_status_check"
    )
    op.execute(
        "ALTER TABLE pilot.engagements ADD CONSTRAINT pilot_engagements_status_check CHECK (status IN ('PREPARING','READY','ACTIVE','COMPLETED','PAUSED'))"
    )
    op.execute(
        "ALTER TABLE pilot.engagements ALTER COLUMN status SET DEFAULT 'PREPARING'"
    )
    op.execute(
        "ALTER TABLE context.activation_runs ADD COLUMN diagnostics JSONB NOT NULL DEFAULT '{}'::jsonb"
    )
    op.execute(
        "ALTER TABLE pipeline.signals ADD COLUMN date_metadata JSONB NOT NULL DEFAULT '{}'::jsonb"
    )
    op.execute(
        "ALTER TABLE context.relevant_monitoring ADD COLUMN last_material_change_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE context.relevant_monitoring ADD COLUMN lens_version INTEGER"
    )
    op.execute("""
        CREATE TABLE context.personalisation_state (
          tenant_id UUID NOT NULL REFERENCES auth.tenants(id),
          user_id UUID PRIMARY KEY,
          FOREIGN KEY (tenant_id,user_id) REFERENCES auth.users(tenant_id,id),
          request_id UUID NOT NULL,
          context_version INTEGER NOT NULL,
          lens_version INTEGER NOT NULL,
          status VARCHAR(20) NOT NULL CHECK (status IN ('QUEUED','RUNNING','COMPLETED','FAILED')),
          requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          started_at TIMESTAMPTZ, completed_at TIMESTAMPTZ,
          outputs_evaluated INTEGER NOT NULL DEFAULT 0,
          error_code VARCHAR(80)
        )
    """)
    op.execute("ALTER TABLE context.personalisation_state ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE context.personalisation_state FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY personalisation_tenant_isolation ON context.personalisation_state
        USING (tenant_id=NULLIF(current_setting('app.current_tenant_id',true),'')::uuid
          OR current_setting('app.system_admin',true)='true')
        WITH CHECK (tenant_id=NULLIF(current_setting('app.current_tenant_id',true),'')::uuid
          OR current_setting('app.system_admin',true)='true')
    """)
    op.execute(
        "GRANT SELECT,INSERT,UPDATE ON context.personalisation_state TO sc_app_runtime"
    )
    op.execute("ALTER TABLE auth.users ADD COLUMN briefing_viewed_through TIMESTAMPTZ")


def downgrade() -> None:
    # PREPARING is an operator lifecycle label; READY on the prior release never
    # granted an invitation automatically. Evidence/counters are retained.
    op.execute("UPDATE pilot.engagements SET status='PAUSED' WHERE status='PREPARING'")
    op.execute(
        "ALTER TABLE pilot.engagements DROP CONSTRAINT pilot_engagements_status_check"
    )
    op.execute(
        "ALTER TABLE pilot.engagements ADD CONSTRAINT pilot_engagements_status_check CHECK (status IN ('READY','ACTIVE','COMPLETED','PAUSED'))"
    )
    op.execute("ALTER TABLE pilot.engagements ALTER COLUMN status SET DEFAULT 'READY'")
    op.execute("ALTER TABLE auth.users DROP COLUMN briefing_viewed_through")
    op.execute("DROP TABLE context.personalisation_state")
    op.execute(
        "ALTER TABLE context.relevant_monitoring DROP COLUMN last_material_change_at"
    )
    op.execute("ALTER TABLE context.relevant_monitoring DROP COLUMN lens_version")
    op.execute("ALTER TABLE pipeline.signals DROP COLUMN date_metadata")
    op.execute("ALTER TABLE context.activation_runs DROP COLUMN diagnostics")
