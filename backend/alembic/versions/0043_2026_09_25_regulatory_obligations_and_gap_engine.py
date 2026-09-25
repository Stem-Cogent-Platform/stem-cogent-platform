"""Evidence-based regulatory audits, policy vault and immutable reviewer history.

Revision ID: 0043
Revises: 0042
"""
from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None

TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid"
TABLES = (
    "organizations.tenant_policies", "organizations.policy_chunks",
    "pipeline.compliance_gap_runs", "pipeline.compliance_gap_audits",
    "audit.compliance_gap_events", "pipeline.marketing_checks",
)


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE SCHEMA IF NOT EXISTS organizations")
    op.execute("GRANT USAGE ON SCHEMA organizations TO sc_app_runtime")
    op.execute("""
    CREATE TABLE pipeline.regulatory_extractions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        signal_id uuid NOT NULL,
        signal_created_at timestamptz NOT NULL,
        source_hash varchar(64) NOT NULL,
        extractor_version varchar(40) NOT NULL,
        source_url text NOT NULL,
        source_text text NOT NULL,
        provider varchar(40) NOT NULL,
        model varchar(100) NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(signal_id,signal_created_at,source_hash,extractor_version),
        UNIQUE(id,signal_id,signal_created_at),
        FOREIGN KEY(signal_id,signal_created_at)
            REFERENCES pipeline.signals(id,created_at) ON DELETE RESTRICT
    )
    """)
    op.execute("""
    CREATE TABLE pipeline.regulatory_obligations (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        extraction_id uuid NOT NULL,
        signal_id uuid NOT NULL,
        signal_created_at timestamptz NOT NULL,
        clause_reference varchar(100) NOT NULL,
        requirement_title text NOT NULL,
        assessment_criteria jsonb NOT NULL,
        applicable_departments text[] NOT NULL DEFAULT '{}',
        source_excerpt text NOT NULL,
        statutory_sanction text,
        statutory_deadline date,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(extraction_id,clause_reference),
        FOREIGN KEY(extraction_id,signal_id,signal_created_at)
            REFERENCES pipeline.regulatory_extractions(id,signal_id,signal_created_at),
        CHECK(jsonb_typeof(assessment_criteria)='array' AND jsonb_array_length(assessment_criteria)>0)
    )
    """)
    op.execute("CREATE INDEX ix_reg_obligations_signal ON pipeline.regulatory_obligations(signal_id)")
    op.execute("""
    CREATE TABLE organizations.tenant_policies (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id uuid NOT NULL REFERENCES auth.tenants(id),
        document_family_id uuid NOT NULL,
        document_title varchar(255) NOT NULL,
        version varchar(20) NOT NULL DEFAULT '1.0',
        file_s3_key text NOT NULL,
        file_s3_version text,
        content_type varchar(150) NOT NULL,
        content_sha256 varchar(64) NOT NULL,
        file_size integer NOT NULL CHECK(file_size>0 AND file_size<=20971520),
        policy_category varchar(50) NOT NULL,
        processing_status varchar(20) NOT NULL DEFAULT 'queued'
            CHECK(processing_status IN ('queued','processing','ready','failed','needs_ocr')),
        error_code varchar(100),
        embedded_chunks_count integer NOT NULL DEFAULT 0 CHECK(embedded_chunks_count>=0),
        active boolean NOT NULL DEFAULT false,
        created_by uuid NOT NULL,
        lease_until timestamptz,
        attempts integer NOT NULL DEFAULT 0,
        created_at timestamptz NOT NULL DEFAULT now(),
        updated_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(organization_id,id),
        UNIQUE(organization_id,document_family_id,version),
        FOREIGN KEY(organization_id,created_by) REFERENCES auth.users(tenant_id,id),
        CHECK(NOT active OR processing_status='ready'),
        CHECK(policy_category IN ('aml_kyc','data_privacy','payment_ops','dispute_resolution','other'))
    )
    """)
    op.execute("CREATE UNIQUE INDEX uq_policy_active_version ON organizations.tenant_policies(organization_id,document_family_id) WHERE active")
    op.execute("CREATE INDEX ix_policies_org_created ON organizations.tenant_policies(organization_id,created_at DESC)")
    op.execute("""
    CREATE TABLE organizations.policy_chunks (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        policy_id uuid NOT NULL,
        organization_id uuid NOT NULL,
        chunk_index integer NOT NULL CHECK(chunk_index>=0),
        content text NOT NULL CHECK(length(content)>0),
        location jsonb NOT NULL DEFAULT '{}',
        token_count integer NOT NULL CHECK(token_count>0 AND token_count<=500),
        embedding vector(1536) NOT NULL,
        embedding_model varchar(100) NOT NULL DEFAULT 'text-embedding-3-small',
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(policy_id,chunk_index),
        FOREIGN KEY(organization_id,policy_id) REFERENCES organizations.tenant_policies(organization_id,id)
    )
    """)
    op.execute("CREATE INDEX ix_policy_chunks_org_policy ON organizations.policy_chunks(organization_id,policy_id)")
    # HNSW has no training requirement; exact tenant-filtered retrieval is used at launch.
    op.execute("CREATE INDEX ix_policy_chunks_vector ON organizations.policy_chunks USING hnsw(embedding vector_cosine_ops)")
    op.execute("""
    CREATE TABLE pipeline.compliance_gap_runs (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id uuid NOT NULL REFERENCES auth.tenants(id),
        signal_id uuid NOT NULL,
        signal_created_at timestamptz NOT NULL,
        extraction_id uuid REFERENCES pipeline.regulatory_extractions(id),
        idempotency_key uuid NOT NULL,
        processing_status varchar(20) NOT NULL DEFAULT 'queued'
            CHECK(processing_status IN ('queued','processing','completed','failed','needs_source')),
        policy_snapshot jsonb NOT NULL DEFAULT '[]',
        engine_version varchar(40) NOT NULL DEFAULT 'gap-v1',
        error_code varchar(100),
        attempts integer NOT NULL DEFAULT 0,
        lease_until timestamptz,
        requested_by uuid,
        created_at timestamptz NOT NULL DEFAULT now(),
        completed_at timestamptz,
        UNIQUE(organization_id,id),
        UNIQUE(organization_id,idempotency_key),
        FOREIGN KEY(signal_id,signal_created_at) REFERENCES pipeline.signals(id,created_at),
        FOREIGN KEY(organization_id,requested_by) REFERENCES auth.users(tenant_id,id)
    )
    """)
    op.execute("CREATE INDEX ix_gap_runs_org_signal ON pipeline.compliance_gap_runs(organization_id,signal_id,created_at DESC)")
    op.execute("""
    CREATE TABLE pipeline.compliance_gap_audits (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id uuid NOT NULL REFERENCES auth.tenants(id),
        obligation_id uuid NOT NULL REFERENCES pipeline.regulatory_obligations(id),
        run_id uuid NOT NULL,
        status varchar(30) NOT NULL CHECK(status IN ('adequately_met','partially_met','gap_deficient')),
        automated_status varchar(30) NOT NULL CHECK(automated_status IN ('adequately_met','partially_met','gap_deficient')),
        evidence_matches jsonb NOT NULL DEFAULT '[]' CHECK(jsonb_typeof(evidence_matches)='array'),
        compliance_score numeric(5,2) NOT NULL DEFAULT 0 CHECK(compliance_score BETWEEN 0 AND 100),
        reviewer_override jsonb,
        revision integer NOT NULL DEFAULT 1 CHECK(revision>0),
        updated_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(organization_id,obligation_id),
        UNIQUE(organization_id,id),
        FOREIGN KEY(organization_id,run_id) REFERENCES pipeline.compliance_gap_runs(organization_id,id)
    )
    """)
    op.execute("CREATE INDEX ix_gap_audits_status ON pipeline.compliance_gap_audits(organization_id,status)")
    op.execute("""
    CREATE TABLE audit.compliance_gap_events (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id uuid NOT NULL REFERENCES auth.tenants(id),
        audit_id uuid NOT NULL,
        actor_user_id uuid,
        event_type varchar(30) NOT NULL CHECK(event_type IN ('assessed','override','addendum','sign_off')),
        idempotency_key uuid NOT NULL,
        revision integer NOT NULL,
        reason text NOT NULL,
        snapshot jsonb NOT NULL CHECK(jsonb_typeof(snapshot)='object'),
        policy_id uuid,
        created_at timestamptz NOT NULL DEFAULT now(),
        UNIQUE(organization_id,audit_id,idempotency_key),
        FOREIGN KEY(organization_id,audit_id) REFERENCES pipeline.compliance_gap_audits(organization_id,id),
        FOREIGN KEY(organization_id,actor_user_id) REFERENCES auth.users(tenant_id,id),
        FOREIGN KEY(organization_id,policy_id) REFERENCES organizations.tenant_policies(organization_id,id)
    )
    """)
    op.execute("CREATE INDEX ix_gap_events_org_audit_time ON audit.compliance_gap_events(organization_id,audit_id,created_at,id)")
    op.execute("CREATE TRIGGER gap_events_reject_mutation BEFORE UPDATE OR DELETE ON audit.compliance_gap_events FOR EACH ROW EXECUTE FUNCTION audit.reject_event_mutation()")
    op.execute("CREATE TRIGGER gap_events_reject_truncate BEFORE TRUNCATE ON audit.compliance_gap_events FOR EACH STATEMENT EXECUTE FUNCTION audit.reject_event_mutation()")
    op.execute("""
    CREATE TABLE pipeline.marketing_checks (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        organization_id uuid NOT NULL REFERENCES auth.tenants(id),
        created_by uuid NOT NULL,
        campaign_copy text NOT NULL,
        channel varchar(30) NOT NULL,
        result jsonb NOT NULL CHECK(jsonb_typeof(result)='object'),
        rules_version varchar(40) NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        FOREIGN KEY(organization_id,created_by) REFERENCES auth.users(tenant_id,id)
    )
    """)
    op.execute("CREATE INDEX ix_marketing_checks_org_created ON pipeline.marketing_checks(organization_id,created_at DESC)")
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"CREATE POLICY tenant_isolation ON {table} USING (organization_id={TENANT}) WITH CHECK (organization_id={TENANT})")
        op.execute(f"GRANT SELECT,INSERT,UPDATE,DELETE ON {table} TO sc_app_runtime")
    op.execute("REVOKE UPDATE,DELETE,TRUNCATE ON audit.compliance_gap_events FROM PUBLIC,sc_app_runtime")
    for table in ("pipeline.regulatory_extractions", "pipeline.regulatory_obligations"):
        op.execute(f"GRANT SELECT,INSERT ON {table} TO sc_app_runtime")
        op.execute(f"REVOKE UPDATE,DELETE,TRUNCATE ON {table} FROM PUBLIC,sc_app_runtime")
    op.execute("UPDATE auth.roles SET permissions=array_append(permissions,'REVIEW_COMPLIANCE') WHERE role_code IN ('ADMIN','ANALYST') AND NOT ('REVIEW_COMPLIANCE'=ANY(permissions))")
    op.execute("UPDATE auth.roles SET permissions=array_append(permissions,'MANAGE_POLICIES') WHERE role_code IN ('ADMIN','ANALYST') AND NOT ('MANAGE_POLICIES'=ANY(permissions))")


def downgrade():
    op.execute("UPDATE auth.roles SET permissions=array_remove(array_remove(permissions,'REVIEW_COMPLIANCE'),'MANAGE_POLICIES')")
    for table in ("pipeline.marketing_checks", "audit.compliance_gap_events", "pipeline.compliance_gap_audits", "pipeline.compliance_gap_runs", "organizations.policy_chunks", "organizations.tenant_policies", "pipeline.regulatory_obligations", "pipeline.regulatory_extractions"):
        op.execute(f"DROP TABLE {table}")
    # The vector extension is shared with signal_embeddings; never remove it here.
