from __future__ import annotations

import importlib.util
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api.auth import Principal, RequestContext
from app.api.v1.compliance import _source_ip
from app.billing.gates import require_feature
from app.compliance import documents, service
from app.core.runtime_config import validate_paystack_key_prefix
from app.core.secrets import SecretConfigurationError


ROOT = Path(__file__).resolve().parents[2]
COMPLIANCE_MIGRATION = (
    ROOT / "alembic" / "versions" / "0016_2026_08_24_create_compliance_ledger.py"
)
RLS_MIGRATION = ROOT / "alembic" / "versions" / "0017_2026_08_24_harden_runtime_rls.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _context(*, accepted: bool) -> RequestContext:
    accepted_at = datetime.now(UTC) if accepted else None
    legal = documents.current_legal_documents()
    principal = Principal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        permission_role="ADMIN",
        permissions=frozenset({"CONFIGURE_COMPANY_CONTEXT"}),
        tos_accepted_at=accepted_at,
        tos_version=legal["terms"].version if accepted else None,
        privacy_policy_accepted_at=accepted_at,
        privacy_policy_version=legal["privacy"].version if accepted else None,
        ndpa_consent_accepted_at=accepted_at,
        ndpa_consent_version=legal["ndpa"].version if accepted else None,
        binding_app_version="0.1.0" if accepted else None,
        current_compliance_ledger_id=uuid4() if accepted else None,
    )
    return RequestContext(principal=principal, session=SimpleNamespace())  # type: ignore[arg-type]


def test_compliance_migration_is_immutable_versioned_and_tenant_isolated() -> None:
    source = COMPLIANCE_MIGRATION.read_text(encoding="utf-8")
    assert "tenant_compliance_ledger" in source
    assert "tos_accepted_at" in source
    assert "privacy_policy_accepted_at" in source
    assert "ndpa_consent_accepted_at" in source
    assert "binding_app_version" in source
    assert "source_ip INET NOT NULL" in source
    assert "consent_signature CHAR(64)" in source
    assert "HMAC-SHA256" in source
    assert "reject_event_mutation" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    module = _load(COMPLIANCE_MIGRATION, "compliance_migration")
    assert module.revision == "0016"
    assert module.down_revision == "0015"


def test_runtime_role_migration_forces_rls_and_removes_owner_bypass() -> None:
    source = RLS_MIGRATION.read_text(encoding="utf-8")
    assert "CREATE ROLE sc_app_runtime" in source
    assert "NOBYPASSRLS" in source
    assert "FORCE ROW LEVEL SECURITY" in source
    assert "REVOKE UPDATE, DELETE, TRUNCATE ON audit.events" in source
    module = _load(RLS_MIGRATION, "runtime_rls_migration")
    assert module.revision == "0017"
    assert module.down_revision == "0016"


def test_legal_documents_are_versioned_hashed_and_use_current_nigeria_framework() -> None:
    bundle = documents.current_legal_documents()
    assert set(bundle) == {"terms", "privacy", "ndpa"}
    assert all(len(document.sha256) == 64 for document in bundle.values())
    assert "Nigeria Data Protection Act 2023" in bundle["ndpa"].body
    assert "General Application and Implementation Directive 2025" in bundle["ndpa"].body
    assert "NDPR compliant" not in bundle["ndpa"].body


def test_company_data_gate_rejects_missing_or_stale_acceptance(monkeypatch) -> None:
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(APPLICATION_VERSION="0.1.0"))
    with pytest.raises(HTTPException) as rejected:
        service.require_current_legal_acceptance(_context(accepted=False))
    assert rejected.value.status_code == 403
    assert rejected.value.detail["code"] == "LEGAL_CONSENT_REQUIRED"
    service.require_current_legal_acceptance(_context(accepted=True))


def test_consent_signature_is_deterministic_and_identity_bound() -> None:
    common = {
        "secret": "server-only-signing-secret",
        "ledger_id": uuid4(),
        "tenant_id": uuid4(),
        "user_id": uuid4(),
        "accepted_at": datetime(2026, 8, 24, 8, 0, tzinfo=UTC),
        "source_ip": "203.0.113.8",
        "user_agent": "Stem-Test/1.0",
        "application_version": "0.1.0",
        "idempotency_key": uuid4(),
    }
    first = service.consent_signature(**common)
    assert first == service.consent_signature(**common)
    assert len(first) == 64
    assert first != service.consent_signature(**{**common, "user_id": uuid4()})


def test_consent_audit_uses_alb_appended_source_ip() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/compliance/consent",
            "headers": [(b"x-forwarded-for", b"198.51.100.20, 203.0.113.8")],
            "client": ("10.0.1.25", 443),
            "server": ("api.stem-cogent.com", 443),
            "scheme": "https",
            "query_string": b"",
        }
    )
    assert _source_ip(request) == "203.0.113.8"


def test_individual_tier_cannot_forge_company_feature_access() -> None:
    request_context = _context(accepted=True)
    individual = replace(
        request_context.principal,
        plan_code="INDIVIDUAL",
        billing_status="ACTIVE",
        entitlements={"company_intelligence_matrix": False},
    )
    with pytest.raises(HTTPException) as rejected:
        require_feature(
            RequestContext(principal=individual, session=SimpleNamespace()),  # type: ignore[arg-type]
            "company_intelligence_matrix",
        )
    assert rejected.value.status_code == 403
    assert rejected.value.detail["code"] == "FEATURE_NOT_INCLUDED"


@pytest.mark.parametrize(
    ("environment", "secret_key", "public_key"),
    [
        ("staging", "sk_test_valid", "pk_test_valid"),
        ("prod", "sk_live_valid", "pk_live_valid"),
        ("production", "sk_live_valid", "pk_live_valid"),
    ],
)
def test_paystack_environment_prefix_contract_accepts_matching_keys(
    environment: str, secret_key: str, public_key: str
) -> None:
    validate_paystack_key_prefix(
        environment=environment, secret_key=secret_key, public_key=public_key
    )


@pytest.mark.parametrize(
    ("environment", "secret_key", "public_key"),
    [
        ("staging", "sk_live_wrong", "pk_test_valid"),
        ("prod", "sk_test_wrong", "pk_live_valid"),
        ("staging", "sk_test_valid", "pk_live_wrong"),
        ("prod", "sk_live_valid", "pk_test_wrong"),
    ],
)
def test_paystack_environment_prefix_contract_fails_closed(
    environment: str, secret_key: str, public_key: str
) -> None:
    with pytest.raises(SecretConfigurationError):
        validate_paystack_key_prefix(
            environment=environment, secret_key=secret_key, public_key=public_key
        )
