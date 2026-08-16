"""Create v2 configuration tables and seed the canonical taxonomy.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-15
"""

import runpy
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SEED = runpy.run_path(
    Path(__file__).resolve().parents[1] / "data" / "0003_config_seed.py"
)
TAXONOMY_VERSION: str = _SEED["TAXONOMY_VERSION"]
CANONICAL_DOMAINS: tuple[str, ...] = _SEED["CANONICAL_DOMAINS"]
TAXONOMY_ROWS: tuple[tuple[str, str, str], ...] = _SEED["TAXONOMY_ROWS"]
DECISION_RULES: tuple[tuple[str, str, str, int, str, str], ...] = _SEED[
    "DECISION_RULES"
]


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _jsonb_literal(value: str) -> str:
    encoded = value.encode("utf-8").hex()
    return f"convert_from(decode('{encoded}', 'hex'), 'UTF8')::JSONB"


def _domain_values() -> str:
    return ", ".join(_sql_literal(domain) for domain in CANONICAL_DOMAINS)


def _create_tables() -> None:
    domains = _domain_values()
    op.execute(
        """
        CREATE TABLE config.sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_code VARCHAR(120) NOT NULL UNIQUE,
            source_name VARCHAR(255) NOT NULL,
            source_type VARCHAR(30) NOT NULL,
            tier SMALLINT NOT NULL,
            base_url TEXT,
            auth_type VARCHAR(30) NOT NULL DEFAULT 'NO_AUTH',
            auth_config_ref TEXT,
            schedule_cron VARCHAR(100),
            priority_class VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
            region VARCHAR(10) NOT NULL DEFAULT 'NG',
            reliability_score NUMERIC(4,3) NOT NULL,
            schema_version VARCHAR(20) NOT NULL DEFAULT '1.0',
            retry_policy JSONB NOT NULL DEFAULT '{}'::JSONB,
            health_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            last_successful_collect TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT sources_tier_positive_check CHECK (tier > 0),
            CONSTRAINT sources_reliability_score_check
                CHECK (reliability_score BETWEEN 0 AND 1),
            CONSTRAINT sources_retry_policy_object_check
                CHECK (jsonb_typeof(retry_policy) = 'object')
        )
        """
    )
    op.execute(
        f"""
        CREATE TABLE config.signal_taxonomy (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            domain_code VARCHAR(50) NOT NULL,
            subcategory_code VARCHAR(100) NOT NULL,
            keyword_patterns JSONB NOT NULL DEFAULT '[]'::JSONB,
            entity_rules JSONB NOT NULL DEFAULT '{{}}'::JSONB,
            urgency_weight NUMERIC(4,3) NOT NULL DEFAULT 0.50,
            version VARCHAR(20) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            CONSTRAINT signal_taxonomy_domain_check
                CHECK (domain_code IN ({domains})),
            CONSTRAINT signal_taxonomy_keyword_patterns_array_check
                CHECK (jsonb_typeof(keyword_patterns) = 'array'),
            CONSTRAINT signal_taxonomy_entity_rules_object_check
                CHECK (jsonb_typeof(entity_rules) = 'object'),
            CONSTRAINT signal_taxonomy_urgency_weight_check
                CHECK (urgency_weight BETWEEN 0 AND 1),
            CONSTRAINT signal_taxonomy_natural_key
                UNIQUE (domain_code, subcategory_code, version)
        )
        """
    )
    op.execute(
        f"""
        CREATE TABLE config.decision_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rule_code VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            domain_code VARCHAR(50),
            conditions JSONB NOT NULL,
            output_contract JSONB NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            version VARCHAR(20) NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT decision_rules_domain_check
                CHECK (domain_code IS NULL OR domain_code IN ({domains})),
            CONSTRAINT decision_rules_conditions_object_check
                CHECK (jsonb_typeof(conditions) = 'object'),
            CONSTRAINT decision_rules_output_contract_object_check
                CHECK (jsonb_typeof(output_contract) = 'object'),
            CONSTRAINT decision_rules_priority_positive_check CHECK (priority > 0)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_sources_operational_selection
            ON config.sources (health_status, tier, priority_class)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_signal_taxonomy_active_domain
            ON config.signal_taxonomy (domain_code, active, version)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_decision_rules_active_priority
            ON config.decision_rules (active, priority, domain_code)
        """
    )


def _seed_taxonomy() -> None:
    values = [
        "("
        + ", ".join(
            (
                _sql_literal(domain),
                _sql_literal(event_type),
                "'[]'::JSONB",
                "'{}'::JSONB",
                weight,
                _sql_literal(TAXONOMY_VERSION),
                "TRUE",
            )
        )
        + ")"
        for domain, event_type, weight in TAXONOMY_ROWS
    ]
    op.execute(
        """
        INSERT INTO config.signal_taxonomy (
            domain_code,
            subcategory_code,
            keyword_patterns,
            entity_rules,
            urgency_weight,
            version,
            active
        ) VALUES
        """
        + ",\n".join(values)
    )


def _seed_decision_rules() -> None:
    values = [
        "("
        + ", ".join(
            (
                _sql_literal(code),
                _sql_literal(name),
                _sql_literal(domain),
                _jsonb_literal(conditions),
                _jsonb_literal(output_contract),
                str(priority),
                _sql_literal(TAXONOMY_VERSION),
                "TRUE",
            )
        )
        + ")"
        for code, name, domain, priority, conditions, output_contract in DECISION_RULES
    ]
    op.execute(
        """
        INSERT INTO config.decision_rules (
            rule_code,
            name,
            domain_code,
            conditions,
            output_contract,
            priority,
            version,
            active
        ) VALUES
        """
        + ",\n".join(values)
    )


def upgrade() -> None:
    _create_tables()
    _seed_taxonomy()
    _seed_decision_rules()


def downgrade() -> None:
    op.execute("DROP TABLE config.decision_rules")
    op.execute("DROP TABLE config.signal_taxonomy")
    op.execute("DROP TABLE config.sources")
