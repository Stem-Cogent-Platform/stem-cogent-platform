"""Tenant competitor dossiers and private field intelligence.

Revision ID: 0044
Revises: 0043
"""
from alembic import op

revision = '0044'
down_revision = '0043'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE pipeline.competitor_dossiers (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id uuid NOT NULL REFERENCES auth.tenants(id),
        competitor_name varchar(150) NOT NULL,
        competitor_key varchar(150) NOT NULL CHECK(length(competitor_key)>0),
        canonical_domain varchar(253),
        known_licenses text[] NOT NULL DEFAULT '{}',
        primary_settlement_rails text[] NOT NULL DEFAULT '{}',
        fee_model_summary text,
        core_target_segments text[] NOT NULL DEFAULT '{}',
        strengths_vs_us jsonb NOT NULL DEFAULT '[]',
        weaknesses_vs_us jsonb NOT NULL DEFAULT '[]',
        profile jsonb NOT NULL DEFAULT '{}',
        evidence jsonb NOT NULL DEFAULT '[]',
        provenance jsonb NOT NULL DEFAULT '{}',
        processing_status varchar(20) NOT NULL DEFAULT 'queued'
            CHECK(processing_status IN ('queued','processing','ready','failed')),
        attempts integer NOT NULL DEFAULT 0,
        lease_until timestamptz,
        error_code varchar(100),
        requested_at timestamptz NOT NULL DEFAULT clock_timestamp(),
        last_refreshed_at timestamptz,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(organization_id,competitor_key), UNIQUE(organization_id,id)
    )''')
    op.execute('CREATE INDEX ix_dossiers_org_name ON pipeline.competitor_dossiers(organization_id,competitor_name)')
    op.execute('''CREATE TABLE organizations.deal_signals (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id uuid NOT NULL REFERENCES auth.tenants(id),
        created_by_user_id uuid NOT NULL,
        competitor_id uuid NOT NULL,
        competitor_name_raw varchar(150) NOT NULL,
        deal_outcome varchar(30) NOT NULL CHECK(deal_outcome IN ('won','lost','churned')),
        merchant_segment varchar(100) NOT NULL CHECK(length(merchant_segment)>0),
        deal_size_arr_or_gmv varchar(100),
        raw_sales_notes text NOT NULL CHECK(length(raw_sales_notes) BETWEEN 10 AND 20000),
        occurred_on date NOT NULL,
        extracted_decision_drivers text[] NOT NULL DEFAULT '{}',
        objections_encountered text[] NOT NULL DEFAULT '{}',
        winning_talk_track text,
        talk_track_kind varchar(20) NOT NULL DEFAULT 'unknown'
            CHECK(talk_track_kind IN ('observed','suggested','unknown')),
        extraction jsonb NOT NULL DEFAULT '{}',
        themes text[] NOT NULL DEFAULT '{}',
        processing_status varchar(20) NOT NULL DEFAULT 'queued'
            CHECK(processing_status IN ('queued','processing','ready','failed')),
        attempts integer NOT NULL DEFAULT 0,
        lease_until timestamptz,
        error_code varchar(100),
        idempotency_key uuid NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        processed_at timestamptz,
        UNIQUE(organization_id,id), UNIQUE(organization_id,idempotency_key),
        FOREIGN KEY(organization_id,created_by_user_id) REFERENCES auth.users(tenant_id,id),
        FOREIGN KEY(organization_id,competitor_id) REFERENCES pipeline.competitor_dossiers(organization_id,id)
    )''')
    op.execute('CREATE INDEX ix_deal_signals_org ON organizations.deal_signals(organization_id,deal_outcome,occurred_on DESC)')
    op.execute('CREATE INDEX ix_deal_signals_competitor ON organizations.deal_signals(organization_id,competitor_id,occurred_on DESC)')
    for table in ('pipeline.competitor_dossiers', 'organizations.deal_signals'):
        op.execute(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY')
        op.execute(f'ALTER TABLE {table} FORCE ROW LEVEL SECURITY')
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING (organization_id=NULLIF(current_setting('app.current_tenant_id',true),'')::uuid) WITH CHECK (organization_id=NULLIF(current_setting('app.current_tenant_id',true),'')::uuid)")
        op.execute(f'GRANT SELECT,INSERT,UPDATE ON {table} TO sc_app_runtime')
        name = table.split('.')[1]
        op.execute(f"CREATE INDEX ix_{name}_recovery ON {table}(organization_id,processing_status,lease_until)")
    op.execute("UPDATE auth.roles SET permissions=array_append(permissions,'MANAGE_COMPETITIVE_INTELLIGENCE') WHERE role_code IN ('ADMIN','ANALYST') AND NOT ('MANAGE_COMPETITIVE_INTELLIGENCE'=ANY(permissions))")


def downgrade():
    op.execute("UPDATE auth.roles SET permissions=array_remove(permissions,'MANAGE_COMPETITIVE_INTELLIGENCE')")
    op.execute('DROP TABLE organizations.deal_signals')
    op.execute('DROP TABLE pipeline.competitor_dossiers')
