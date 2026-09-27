"""Keep reports synthesized from private tenant evidence inside that tenant.

Revision ID: 0047
Revises: 0046
"""
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade():
    # Older unscoped reports remain quarantined (NULL tenant), never reassigned.
    op.execute("ALTER TABLE pipeline.market_reports ADD COLUMN tenant_id UUID REFERENCES auth.tenants(id)")
    op.execute("ALTER TABLE pipeline.market_reports DROP CONSTRAINT IF EXISTS market_reports_sector_slug_key")
    op.execute("CREATE UNIQUE INDEX market_reports_tenant_sector ON pipeline.market_reports(tenant_id, sector_slug)")
    op.execute("ALTER TABLE pipeline.market_reports ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pipeline.market_reports FORCE ROW LEVEL SECURITY")
    op.execute("""CREATE POLICY market_reports_tenant ON pipeline.market_reports
        USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
        WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)""")


def downgrade():
    raise RuntimeError("Tenant-scoped reports cannot safely be reverted to a shared cache")
