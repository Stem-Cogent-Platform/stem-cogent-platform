from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.api.v1.admin import TenantProvisionInput
from app.api.v1.context import OnboardingCompleteInput
from app.context.completeness import company_context_status


ROOT = Path(__file__).resolve().parents[3]


def test_company_context_uses_one_explicit_completeness_contract() -> None:
    profile = {
        "version": 7,
        "business_categories": ["Payments"],
        "operating_markets": ["NG"],
        "strategic_priorities": ["Reliability"],
    }
    complete = company_context_status(
        profile,
        [{"object_type": "PRODUCT", "name": "Merchant payments", "active": True}],
    )
    incomplete = company_context_status(profile, [])

    assert complete == {
        "version": 7,
        "complete": True,
        "completeness": 1.0,
        "missing_fields": [],
    }
    assert incomplete["complete"] is False
    assert incomplete["missing_fields"] == ["products"]


def test_onboarding_delivery_contract_separates_threshold_and_digest() -> None:
    value = OnboardingCompleteInput(
        alert_threshold="IMPORTANT_AND_CRITICAL",
        digest_cadence="WEEKLY",
    )

    assert value.alert_threshold == "IMPORTANT_AND_CRITICAL"
    assert value.digest_cadence == "WEEKLY"


@pytest.mark.parametrize(
    "name",
    ["Stem Phase 5 Pilot", "Canonical Pilot", "Acme Staging", "QA Fixture"],
)
def test_customer_tenant_name_rejects_internal_execution_terms(name: str) -> None:
    with pytest.raises(ValidationError, match="customer's real company display name"):
        TenantProvisionInput(
            canonical_company_name=name,
            company_website="https://example.com",
            business_categories=["Payments"],
            markets=["NG"],
            products=["Merchant payments"],
            strategic_priorities=["Reliability"],
            pilot_owner="Stem pilot owner",
        )


def test_onboarding_ui_has_independent_delivery_controls_and_durable_completion() -> None:
    source = (ROOT / "frontend/src/components/onboarding-wizard.tsx").read_text()

    assert "alertThresholds" in source
    assert "digestCadences" in source
    assert 'apiRequest("/api/v1/me/onboarding/complete"' in source
    assert "DAILY_BRIEFING" not in source
    assert "WEEKLY_BRIEFING" not in source


def test_live_acceptance_migration_is_staging_forward_compatible() -> None:
    source = (
        ROOT
        / "backend/alembic/versions/0028_2026_09_04_live_acceptance_integrity.py"
    ).read_text()

    assert 'down_revision: str | None = "0027"' in source
    assert "onboarding_completed_at" in source
    assert "content_fingerprint" in source
    assert "embedding_input_version" in source


def test_invitation_repair_preserves_deployed_function_contract() -> None:
    source = (
        ROOT
        / "backend/alembic/versions/0026_2026_09_03_fix_invitation_acceptance.py"
    ).read_text()

    original = (
        ROOT / "backend/alembic/versions/0023_2026_08_31_phase5_pilot_invites_and_activation.py"
    ).read_text()
    assert "email VARCHAR" in source
    assert "email VARCHAR" in original
    assert "ON CONFLICT ON CONSTRAINT users_tenant_email_key" in source


def test_embedding_and_synthesis_cost_identities_precede_provider_work() -> None:
    embedding = (ROOT / "backend/app/workers/tasks/embedding.py").read_text()
    synthesis = (ROOT / "backend/app/workers/tasks/synthesis.py").read_text()

    assert embedding.index("_cached_embedding(") < embedding.index("_embedding_client()")
    assert "embedding_input_version=:input_version" in embedding
    assert "pg_advisory_xact_lock" in embedding
    assert synthesis.index("synthesis_prompt_version=:prompt_version") < synthesis.index(
        "_synthesis_client()"
    )
    assert 'return "ALREADY_SYNTHESIZED"' in synthesis


def test_cil_records_provider_and_binds_analytics_boolean_explicitly() -> None:
    api = (ROOT / "backend/app/api/v1/cil.py").read_text()
    answering = (ROOT / "backend/app/cil/answering.py").read_text()
    retrieval = (ROOT / "backend/app/cil/retrieval.py").read_text()
    component = (ROOT / "frontend/src/components/cil-panel.tsx").read_text()

    assert "CAST(:grounded AS BOOLEAN)" in api
    assert '"provider": provider' in api
    assert "CIL_RATE_LIMIT_PER_MINUTE" in api
    assert "settings.OPENAI_API_KEY_ARN or settings.GROQ_API_KEY_ARN" in answering
    assert '(), (), (), (), "INSUFFICIENT_DATA"' in retrieval
    assert "hasRelationships" in component


def test_monitoring_contract_requires_identity_evidence_and_relevance() -> None:
    product = (ROOT / "backend/app/api/v1/product.py").read_text()
    activation = (ROOT / "backend/app/workers/tasks/pilot_activation.py").read_text()

    for required in (
        "display_title",
        "event_type",
        "source_name",
        "relevance_trace",
    ):
        assert required in product
    assert "jsonb_array_length(output.citations)>0" in activation
    assert "matched_object_ids" in activation


def test_live_staging_runtime_repairs_are_present_in_canonical_source() -> None:
    celery = (ROOT / "backend/app/workers/celery_app.py").read_text()
    logging = (ROOT / "backend/app/core/logging.py").read_text()
    iam = (ROOT / "infrastructure/terraform/modules/iam/main.tf").read_text()
    staging = (
        ROOT / "infrastructure/terraform/environments/staging/ecs.tf"
    ).read_text()

    assert 'Exchange(name, type="direct")' in celery
    assert "_safe_log_message" in logging
    assert '"system_admin_mfa_secret"' in iam
    assert '"pipeline-synthesized"' in iam
    assert 'PHASE5_PILOT_INVITES_ENABLED          = "true"' in staging
