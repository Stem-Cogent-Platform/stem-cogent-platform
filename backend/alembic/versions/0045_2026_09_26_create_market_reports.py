"""Create pipeline.market_reports for vertical intelligence engine.

Revision ID: 0045
Revises: 0044
"""
from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE pipeline.market_reports (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        sector_slug VARCHAR(100) NOT NULL UNIQUE,
        sector_title VARCHAR(200) NOT NULL,
        primary_jurisdiction VARCHAR(50) NOT NULL DEFAULT 'Nigeria',
        report_payload JSONB NOT NULL,
        monitored_entities_count INT NOT NULL DEFAULT 0,
        last_generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT chk_market_reports_payload_object CHECK (jsonb_typeof(report_payload) = 'object'),
        CONSTRAINT chk_market_reports_entities_nonneg CHECK (monitored_entities_count >= 0)
    );
    """)
    op.execute("CREATE INDEX ix_market_reports_slug ON pipeline.market_reports (sector_slug);")
    op.execute("CREATE INDEX ix_market_reports_last_generated ON pipeline.market_reports (last_generated_at DESC);")
    op.execute("GRANT SELECT, INSERT, UPDATE ON pipeline.market_reports TO sc_app_runtime;")


def downgrade():
    op.execute("DROP TABLE IF EXISTS pipeline.market_reports CASCADE;")
