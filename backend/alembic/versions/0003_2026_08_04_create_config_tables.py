"""Create source registry, taxonomy, and recommendation configuration.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE config.sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_name VARCHAR(255) NOT NULL,
            source_slug VARCHAR(100) NOT NULL UNIQUE,
            source_type VARCHAR(50) NOT NULL CHECK (
                source_type IN (
                    'API', 'RSS_FEED', 'WEB_SCRAPER', 'HTML', 'PDF_DOWNLOAD',
                    'USER_UPLOAD', 'SEARCH', 'PARTNER_FEED'
                )
            ),
            tier SMALLINT NOT NULL CHECK (tier BETWEEN 1 AND 7),
            base_url TEXT,
            auth_type VARCHAR(50) NOT NULL DEFAULT 'NO_AUTH'
                CHECK (auth_type IN ('NO_AUTH', 'API_KEY', 'OAUTH2', 'COOKIE_SESSION')),
            auth_config_ref VARCHAR(512),
            schedule_cron VARCHAR(100),
            priority_class VARCHAR(20) NOT NULL DEFAULT 'STANDARD'
                CHECK (priority_class IN ('CRITICAL', 'HIGH', 'STANDARD', 'LOW')),
            region VARCHAR(10) NOT NULL DEFAULT 'NG',
            signal_domains TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            reliability_score NUMERIC(4,3) NOT NULL DEFAULT 0.700
                CHECK (reliability_score BETWEEN 0 AND 1),
            manipulation_risk NUMERIC(4,3) NOT NULL DEFAULT 0.100
                CHECK (manipulation_risk BETWEEN 0 AND 1),
            schema_version VARCHAR(20) NOT NULL DEFAULT '1.0',
            health_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                CHECK (health_status IN ('ACTIVE', 'DEGRADED', 'PAUSED', 'FAILED')),
            consecutive_failures INTEGER NOT NULL DEFAULT 0
                CHECK (consecutive_failures >= 0),
            last_successful_collect TIMESTAMPTZ,
            last_failure_reason VARCHAR(255),
            total_signals_collected BIGINT NOT NULL DEFAULT 0
                CHECK (total_signals_collected >= 0),
            collector_config JSONB NOT NULL DEFAULT '{}'::JSONB,
            retry_policy JSONB NOT NULL DEFAULT jsonb_build_object(
                'max_retries', 3,
                'backoff_strategy', 'EXPONENTIAL',
                'initial_delay_seconds', 30
            ),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_by UUID REFERENCES auth.users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_sources_health_status ON config.sources(health_status)"
    )
    op.execute("CREATE INDEX idx_sources_tier ON config.sources(tier)")
    op.execute(
        "CREATE INDEX idx_sources_priority_class ON config.sources(priority_class)"
    )
    op.execute("CREATE INDEX idx_sources_region ON config.sources(region)")
    op.execute("CREATE INDEX idx_sources_is_active ON config.sources(is_active)")

    op.execute(
        """
        CREATE TABLE config.source_schema_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id UUID NOT NULL REFERENCES config.sources(id) ON DELETE CASCADE,
            version VARCHAR(20) NOT NULL,
            schema_def JSONB NOT NULL,
            is_current BOOLEAN NOT NULL DEFAULT FALSE,
            migrated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_source_schema_version UNIQUE (source_id, version)
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_source_schema_source_id "
        "ON config.source_schema_versions(source_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX idx_source_schema_current "
        "ON config.source_schema_versions(source_id) WHERE is_current = TRUE"
    )

    op.execute(
        """
        CREATE TABLE config.signal_taxonomy (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            taxonomy_version VARCHAR(20) NOT NULL,
            domain_code VARCHAR(50) NOT NULL,
            domain_label VARCHAR(100) NOT NULL,
            subcategory_code VARCHAR(100),
            subcategory_label VARCHAR(100),
            level SMALLINT NOT NULL CHECK (level IN (1, 2, 3)),
            parent_domain_code VARCHAR(50),
            urgency_weight NUMERIC(4,3) NOT NULL DEFAULT 0.500
                CHECK (urgency_weight BETWEEN 0 AND 1),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_taxonomy_hierarchy CHECK (
                (level = 1 AND parent_domain_code IS NULL)
                OR (level > 1 AND parent_domain_code IS NOT NULL)
            )
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX idx_taxonomy_version_code "
        "ON config.signal_taxonomy "
        "(taxonomy_version, domain_code, subcategory_code) NULLS NOT DISTINCT"
    )
    op.execute(
        "CREATE INDEX idx_taxonomy_domain_code "
        "ON config.signal_taxonomy(domain_code)"
    )
    op.execute(
        "CREATE INDEX idx_taxonomy_version "
        "ON config.signal_taxonomy(taxonomy_version)"
    )

    op.execute(
        """
        CREATE TABLE config.recommendation_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rule_name VARCHAR(255) NOT NULL UNIQUE,
            rule_description TEXT,
            conditions JSONB NOT NULL,
            recommendation_type VARCHAR(100) NOT NULL,
            recommendation_priority VARCHAR(20) NOT NULL
                CHECK (recommendation_priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
            alert_threshold VARCHAR(20)
                CHECK (
                    alert_threshold IS NULL
                    OR alert_threshold IN ('CRITICAL', 'HIGH', 'STANDARD')
                ),
            evaluation_order SMALLINT NOT NULL UNIQUE CHECK (evaluation_order > 0),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
            created_by UUID REFERENCES auth.users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_rec_rules_is_active "
        "ON config.recommendation_rules(is_active)"
    )

    op.execute(
        """
        INSERT INTO config.signal_taxonomy (
            taxonomy_version, domain_code, domain_label, level,
            urgency_weight, is_active
        ) VALUES
            ('2026.06', 'REGULATORY', 'Regulatory', 1, 0.900, TRUE),
            ('2026.06', 'COMPETITIVE', 'Competitive', 1, 0.650, TRUE),
            ('2026.06', 'CONSUMER', 'Consumer', 1, 0.600, TRUE),
            ('2026.06', 'OPERATIONAL', 'Operational', 1, 0.800, TRUE),
            ('2026.06', 'FINANCIAL', 'Financial', 1, 0.800, TRUE),
            ('2026.06', 'INFRASTRUCTURE', 'Infrastructure', 1, 0.880, TRUE),
            ('2026.06', 'ECOSYSTEM', 'Ecosystem', 1, 0.450, TRUE),
            ('2026.06', 'MARKET_EXPANSION', 'Market Expansion', 1, 0.550, TRUE),
            ('2026.06', 'FRAUD_RISK', 'Fraud & Risk', 1, 0.850, TRUE),
            ('2026.06', 'PARTNERSHIP', 'Partnership', 1, 0.500, TRUE),
            ('2026.06', 'PRODUCT', 'Product', 1, 0.500, TRUE),
            ('2026.06', 'TALENT_ORG', 'Talent & Organization', 1, 0.450, TRUE),
            ('2026.06', 'CAPITAL_FUNDING', 'Capital & Funding', 1, 0.550, TRUE),
            ('2026.06', 'MACROECONOMIC', 'Macroeconomic', 1, 0.750, TRUE),
            ('2026.06', 'CROSS_BORDER', 'Cross-Border', 1, 0.600, TRUE),
            ('2026.06', 'TECHNOLOGY', 'Technology', 1, 0.450, TRUE),
            ('2026.06', 'REPUTATION', 'Reputation', 1, 0.650, TRUE),
            ('2026.06', 'BEHAVIORAL', 'Behavioral', 1, 0.500, TRUE),
            ('2026.06', 'DISTRIBUTION', 'Distribution', 1, 0.450, TRUE),
            ('2026.06', 'STRATEGIC', 'Strategic', 1, 0.550, TRUE)
        """
    )
    op.execute(
        """
        INSERT INTO config.recommendation_rules (
            rule_name, rule_description, conditions, recommendation_type,
            recommendation_priority, alert_threshold, evaluation_order
        ) VALUES
        (
            'CRITICAL_REGULATORY',
            'Critical, high-confidence regulatory signal.',
            jsonb_build_object(
                'primary_domain', 'REGULATORY',
                'urgency_score_min', 0.90,
                'confidence_score_min', 0.85
            ),
            'COMPLIANCE_ACTION_REQUIRED', 'CRITICAL', 'CRITICAL', 10
        ),
        (
            'REGULATORY_HIGH_CONFIDENCE_URGENCY',
            'High-confidence regulatory signal above the urgency threshold.',
            jsonb_build_object(
                'primary_domain', 'REGULATORY',
                'urgency_score_min', 0.75,
                'confidence_score_min', 0.80,
                'entity_types_any', jsonb_build_array('REGULATOR_NG')
            ),
            'COMPLIANCE_ACTION_REQUIRED', 'HIGH', 'HIGH', 20
        ),
        (
            'INFRASTRUCTURE_FAILURE',
            'Infrastructure failure with elevated urgency.',
            jsonb_build_object(
                'risk_flags_any', jsonb_build_array('INFRASTRUCTURE_FAILURE'),
                'urgency_score_min', 0.70
            ),
            'OPERATIONAL_RISK_ALERT', 'HIGH', 'HIGH', 30
        ),
        (
            'COMPETITIVE_CLUSTER_ACCELERATING',
            'Accelerating competitive cluster with sufficient confidence.',
            jsonb_build_object(
                'primary_domain', 'COMPETITIVE',
                'cluster_status', 'ACCELERATING',
                'confidence_score_min', 0.70
            ),
            'COMPETITIVE_MONITORING_ESCALATE', 'MEDIUM', 'STANDARD', 40
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE config.recommendation_rules")
    op.execute("DROP TABLE config.signal_taxonomy")
    op.execute("DROP TABLE config.source_schema_versions")
    op.execute("DROP TABLE config.sources")
