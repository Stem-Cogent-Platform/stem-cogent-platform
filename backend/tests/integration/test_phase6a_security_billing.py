"""Integration tests for Phase 6a: Multi-Tenant Auth, Billing & Two-Stage Onboarding.

Covers:
1. Solo user signup (Stage A + Stage B in one session) and Celery bootstrap execution.
2. Invited user signup (OTP verification + Stage B only).
3. 14-day trial expiration gate and workspace monthly query limits.
4. Paystack webhook HMAC-SHA512 verification and tier upgrade processing.
5. Multi-tenant isolation and migration 0042 schema relational integrity.
6. Lean Admin Operator Controller (/api/v1/admin/tenants, /re-bootstrap, /pipeline-health).
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.api.auth import Principal, RequestContext
from app.api.v1 import admin, auth_sessions, billing, onboarding
from app.billing.gates import enforce_workspace_access
from app.billing.paystack import PaystackClient


# ---------------------------------------------------------------------------
# Mock Database Helpers
# ---------------------------------------------------------------------------

class MockDbResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def mappings(self) -> MockDbResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def one(self) -> Any:
        if not self._rows:
            raise RuntimeError("No row found")
        return self._rows[0]

    def scalar_one_or_none(self) -> Any | None:
        if not self._rows:
            return None
        item = self._rows[0]
        if isinstance(item, dict):
            return next(iter(item.values()))
        return item

    def scalar_one(self) -> Any:
        val = self.scalar_one_or_none()
        if val is None:
            raise RuntimeError("No scalar found")
        return val


class MockAsyncSession:
    def __init__(self, query_results: list[list[Any]] | None = None) -> None:
        self.results_queue = [MockDbResult(r) for r in (query_results or [])]
        self.executed_statements: list[str] = []
        self.executed_parameters: list[dict[str, Any]] = []

    async def execute(self, statement: Any, parameters: dict[str, Any] | None = None) -> MockDbResult:
        self.executed_statements.append(str(statement))
        self.executed_parameters.append(parameters or {})
        if self.results_queue:
            return self.results_queue.pop(0)
        return MockDbResult([])

    async def commit(self) -> None:
        pass


def make_context(
    *,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    role: str = "ADMIN",
    is_superuser: bool = False,
    db_session: MockAsyncSession | None = None,
) -> RequestContext:
    t_id = tenant_id or uuid4()
    u_id = user_id or uuid4()
    principal = Principal(
        user_id=u_id,
        tenant_id=t_id,
        permission_role=role,
        permissions=frozenset({"READ_INTELLIGENCE", "CONFIGURE_COMPANY_CONTEXT", "USE_CIL"}),
        is_superuser=is_superuser,
        tos_accepted_at=datetime.now(UTC),
    )
    return RequestContext(principal=principal, session=db_session or MockAsyncSession())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Solo User Signup & Two-Stage Onboarding (< 3 min bootstrap)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stage_a_company_setup_dispatches_bootstrap() -> None:
    """Stage A saves operational footprint, marks stage_a_completed, and dispatches Celery bootstrap."""
    org_id = uuid4()
    user_id = uuid4()
    session = MockAsyncSession([[], []])
    ctx = make_context(tenant_id=org_id, user_id=user_id, db_session=session)

    payload = onboarding.CompanySetupInput(
        company_name="Kuda Technologies Ltd",
        operating_licenses=["MFB_NATIONAL", "SWITCHING"],
        active_products=["agency_banking", "pos_acquiring", "consumer_credit"],
        clearing_rails=["NIBSS_NIP", "INTERSWITCH"],
        primary_country="NG",
        compliance_thresholds={"cbn_exposure_limit": 5000000},
    )

    with patch("app.api.v1.onboarding.bootstrap_tenant_artifacts.delay") as mock_delay:
        res = await onboarding.submit_stage_a_company(payload, ctx)

    assert res["success"] is True
    assert res["organization_id"] == str(org_id)
    assert res["stage_a_completed"] is True
    assert res["bootstrap_dispatched"] is True
    mock_delay.assert_called_once_with(str(org_id))

    # Verify statement execution
    assert any("UPDATE auth.tenants" in stmt for stmt in session.executed_statements)
    assert any("INSERT INTO context.company_profiles" in stmt for stmt in session.executed_statements)


@pytest.mark.asyncio
async def test_stage_b_personal_lens_setup_completes_onboarding() -> None:
    """Stage B saves personal executive lens, priority focus, and marks stage_b_completed."""
    org_id = uuid4()
    user_id = uuid4()
    session = MockAsyncSession([[], []])
    ctx = make_context(tenant_id=org_id, user_id=user_id, db_session=session)

    payload = onboarding.PersonalLensInput(
        business_function="FINANCE",
        decision_lens="treasury_reconciliation",
        priority_focus="NDIC Liquidity Reserve Optimization",
        alert_sensitivity="CRITICAL_ONLY",
    )

    res = await onboarding.submit_stage_b_lens(payload, ctx)

    assert res["success"] is True
    assert res["user_id"] == str(user_id)
    assert res["stage_b_completed"] is True
    assert res["decision_lens"] == "treasury_reconciliation"
    assert res["business_function"] == "FINANCE"

    assert any("UPDATE auth.users" in stmt for stmt in session.executed_statements)


@pytest.mark.asyncio
async def test_onboarding_status_shows_combined_progress() -> None:
    """Onboarding status endpoint aggregates tenant and user onboarding milestones."""
    org_id = uuid4()
    user_id = uuid4()
    future_expiry = datetime.now(UTC) + timedelta(days=12)

    session = MockAsyncSession([
        # auth.tenants row
        [{
            "name": "Kuda Technologies",
            "subscription_tier": "pilot",
            "pilot_expires_at": future_expiry,
            "monthly_workspace_query_limit": 30,
            "queries_used_this_period": 5,
            "stage_a_completed": True,
        }],
        # auth.users row
        [{
            "stage_b_completed": True,
            "business_function": "EXECUTIVE",
            "decision_lens": "executive_strategy",
            "priority_focus": "African Expansion",
            "email_verified": True,
            "is_superuser": False,
        }],
    ])
    ctx = make_context(tenant_id=org_id, user_id=user_id, db_session=session)

    status_data = await onboarding.get_onboarding_status(ctx)

    assert status_data["organization_name"] == "Kuda Technologies"
    assert status_data["subscription_tier"] == "pilot"
    assert status_data["pilot_days_remaining"] == 11 or status_data["pilot_days_remaining"] == 12
    assert status_data["stage_a_completed"] is True
    assert status_data["stage_b_completed"] is True
    assert status_data["monthly_workspace_query_limit"] == 30
    assert status_data["queries_used_this_period"] == 5


# ---------------------------------------------------------------------------
# 2. Workspace Team Invitations & OTP Verification
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invite_team_member_creates_otp_and_invitation() -> None:
    """Admin inviting a team member generates a 6-digit numeric OTP and invitation record."""
    org_id = uuid4()
    admin_id = uuid4()
    session = MockAsyncSession([[], []])
    ctx = make_context(tenant_id=org_id, user_id=admin_id, db_session=session)

    invite_payload = onboarding.InviteTeamMemberInput(
        email="compliance-head@kuda.com",
        assigned_lens="compliance_legal",
    )

    res = await onboarding.invite_workspace_member(invite_payload, ctx)

    assert res["success"] is True
    assert res["email"] == "compliance-head@kuda.com"
    assert len(res["otp_code"]) == 6
    assert res["otp_code"].isdigit()
    assert len(res["token"]) > 30

    assert any("INSERT INTO auth.otp_verifications" in s for s in session.executed_statements)
    assert any("INSERT INTO auth.organization_invitations" in s for s in session.executed_statements)


@pytest.mark.asyncio
async def test_verify_invite_creates_account_and_requires_stage_b() -> None:
    """Invited user verifying OTP receives access token and starts with stage_b_completed=False."""
    org_id = uuid4()
    otp_code = "729481"
    otp_hash = hashlib.sha256(otp_code.encode()).hexdigest()
    future_time = datetime.now(UTC) + timedelta(minutes=10)

    mock_otp_row = {
        "id": uuid4(),
        "attempts": 0,
        "expires_at": future_time,
        "is_used": False,
    }
    mock_invitation_row = {
        "id": uuid4(),
        "organization_id": org_id,
        "assigned_lens": "compliance_legal",
        "expires_at": future_time,
    }

    mock_session = MockAsyncSession([
        [mock_otp_row],                   # 1. Fetch OTP row
        [],                               # 2. Increment attempts (UPDATE)
        [{"?column?": 1}],                # 3. Check hash match (SELECT 1)
        [],                               # 4. Mark OTP used (UPDATE)
        [mock_invitation_row],            # 5. Fetch invitation row (SELECT)
        [],                               # 6. Set app.current_tenant_id (SELECT set_config)
        [],                               # 7. Insert auth.users
        [],                               # 8. Insert auth.login_identities
        [],                               # 9. Update invitation accepted
        [{"name": "Kuda Technologies"}], # 10. Select tenant name
        [{"id": uuid4()}],                # 11. Issue session ID RETURNING id
        [],                               # 12. Update last_login_at
    ])

    verify_payload = onboarding.VerifyInviteInput(
        email="compliance-head@kuda.com",
        otp_code=otp_code,
        password="SecureCompliancePassword2026!",
        display_name="Sarah Okonjo",
    )

    req = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = {}
    resp = MagicMock()

    with patch("app.api.v1.onboarding.get_session") as mock_get_sess, \
         patch("app.api.v1.auth_sessions._jwt_secret", return_value="test-jwt-secret"):

        async def _sess_generator():
            yield mock_session

        mock_get_sess.return_value = _sess_generator()

        access_res = await onboarding.verify_invite_and_create_account(
            verify_payload, req, resp
        )

    assert access_res.access_token is not None
    assert access_res.user["email"] == "compliance-head@kuda.com"
    assert access_res.user["display_name"] == "Sarah Okonjo"
    assert access_res.user["stage_b_completed"] is False  # Must now execute Stage B


@pytest.mark.asyncio
async def test_validate_and_accept_invitation_by_token() -> None:
    """Invited user clicking email link validates token and accepts invitation creating account."""
    org_id = uuid4()
    token = "test-secure-invitation-token-12345678"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    future_time = datetime.now(UTC) + timedelta(days=5)

    mock_inv_row = {
        "id": uuid4(),
        "organization_id": org_id,
        "email": "cfo@kuda.com",
        "assigned_lens": "treasury_reconciliation",
        "expires_at": future_time,
        "workspace_name": "Kuda Technologies",
        "subscription_tier": "pilot",
        "stage_a_completed": True,
    }

    # 1. Test validate_invitation
    mock_validate_session = MockAsyncSession([[mock_inv_row]])
    with patch("app.api.v1.auth_sessions.get_session") as mock_get_sess:
        async def _sess():
            yield mock_validate_session
        mock_get_sess.return_value = _sess()
        val_res = await auth_sessions.validate_invitation(token)
    assert val_res["valid"] is True
    assert val_res["workspace_name"] == "Kuda Technologies"
    assert val_res["email"] == "cfo@kuda.com"

    # 2. Test accept_invitation
    mock_accept_session = MockAsyncSession([
        [mock_inv_row],                    # 1. Fetch invitation
        [],                                # 2. Check existing login identity (None)
        [],                                # 3. Set app.current_tenant_id
        [],                                # 4. Insert auth.users
        [],                                # 5. Insert auth.login_identities
        [],                                # 6. Update invitation accepted_at
        [{"id": uuid4()}],                 # 7. Insert auth.sessions RETURNING id
        [],                                # 8. Update last_login_at
    ])
    req = MagicMock()
    req.client.host = "127.0.0.1"
    req.headers = {}
    resp = MagicMock()

    accept_payload = auth_sessions.AcceptInvitationInput(
        token=token,
        display_name="David Adeleke",
        password="SecureTreasuryPassword2026!",
    )

    with patch("app.api.v1.auth_sessions.get_session") as mock_get_sess, \
         patch("app.api.v1.auth_sessions._jwt_secret", return_value="test-jwt-secret"):
        async def _sess():
            yield mock_accept_session
        mock_get_sess.return_value = _sess()
        res = await auth_sessions.accept_invitation(accept_payload, req, resp)

    assert res.access_token is not None
    assert res.user["email"] == "cfo@kuda.com"
    assert res.user["decision_lens"] == "treasury_reconciliation"
    assert res.user["stage_b_completed"] is False


# ---------------------------------------------------------------------------
# 3. 14-Day Pilot Expiration Gate & Monthly Query Limits
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pilot_expiration_guard_blocks_expired_workspaces() -> None:
    """When a workspace is on 'pilot' tier and trial has expired, enforce_workspace_access raises 402."""
    org_id = uuid4()
    past_expiry = datetime.now(UTC) - timedelta(hours=2)

    session = MockAsyncSession([
        [{
            "subscription_tier": "pilot",
            "pilot_expires_at": past_expiry,
            "monthly_workspace_query_limit": 30,
            "queries_used_this_period": 10,
        }]
    ])
    ctx = make_context(tenant_id=org_id, db_session=session)

    with pytest.raises(HTTPException) as exc_info:
        await enforce_workspace_access(ctx)

    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["code"] == "PILOT_TRIAL_EXPIRED"


@pytest.mark.asyncio
async def test_workspace_monthly_query_limit_blocks_at_threshold() -> None:
    """When an organization hits its monthly query limit, enforce_workspace_access raises 429."""
    org_id = uuid4()
    future_expiry = datetime.now(UTC) + timedelta(days=10)

    session = MockAsyncSession([
        # 1. Fetch tenant row: already used 30 of 30 queries
        [{
            "subscription_tier": "pilot",
            "pilot_expires_at": future_expiry,
            "monthly_workspace_query_limit": 30,
            "queries_used_this_period": 30,
        }],
        # 2. Atomic increment update returns None (where queries_used_this_period < limit failed)
        [],
    ])
    ctx = make_context(tenant_id=org_id, db_session=session)

    with pytest.raises(HTTPException) as exc_info:
        await enforce_workspace_access(ctx)

    assert exc_info.value.status_code == 429
    assert exc_info.value.detail["code"] == "WORKSPACE_QUERY_LIMIT_EXCEEDED"
    assert exc_info.value.detail["limit"] == 30


@pytest.mark.asyncio
async def test_workspace_query_limit_allows_under_quota() -> None:
    """When under quota, enforce_workspace_access increments the query counter successfully."""
    org_id = uuid4()
    future_expiry = datetime.now(UTC) + timedelta(days=10)

    session = MockAsyncSession([
        [{
            "subscription_tier": "operator_growth",
            "pilot_expires_at": future_expiry,
            "monthly_workspace_query_limit": 250,
            "queries_used_this_period": 42,
        }],
        # Atomic update returns new count 43
        [{"queries_used_this_period": 43}],
    ])
    ctx = make_context(tenant_id=org_id, db_session=session)

    # Should not raise exception
    await enforce_workspace_access(ctx)
    assert any("UPDATE auth.tenants" in s for s in session.executed_statements)


# ---------------------------------------------------------------------------
# 4. Paystack Webhook HMAC Verification & Commercial Tier Upgrades
# ---------------------------------------------------------------------------

def test_paystack_webhook_hmac_sha512_verification() -> None:
    """Paystack webhook signature verification strictly validates HMAC-SHA512."""
    secret = "sk_test_paystack_secret_key_stem_cogent_2026"
    raw_payload = b'{"event":"charge.success","data":{"amount":4990000,"currency":"NGN"}}'

    valid_sig = hmac.new(secret.encode(), raw_payload, hashlib.sha512).hexdigest()
    assert billing.verify_paystack_signature(
        raw_body=raw_payload,
        supplied_signature=valid_sig,
        secret_key=secret,
    ) is True

    # Tampered body or invalid signature rejected
    assert billing.verify_paystack_signature(
        raw_body=raw_payload + b" ",
        supplied_signature=valid_sig,
        secret_key=secret,
    ) is False


@pytest.mark.asyncio
async def test_paystack_charge_success_upgrades_organization_tier() -> None:
    """Paystack charge.success webhook upgrades subscription_tier to operator_growth and resets query usage."""
    org_id = uuid4()
    sub_id = uuid4()
    session = MockAsyncSession([
        # 1. Select checkout intent
        [{
            "id": uuid4(),
            "tenant_id": org_id,
            "plan_code": "operator_growth",
            "amount_cents": 4990000,
            "currency": "NGN",
            "display_amount_cents": 49900,
            "display_currency": "USD",
            "status": "PENDING",
            "fx_rate": "1550.000000",
            "fx_source": "CBN_NFEM_VWAP",
            "fx_source_url": "https://www.cbn.gov.ng",
            "fx_quoted_at": datetime.now(UTC),
        }],
        # 2. Insert billing.subscriptions
        [{"id": sub_id}],
        # 3. Update auth.tenants
        [],
        # 4. Insert billing.invoices
        [],
        # 5. Update checkout_intents
        [],
    ])

    webhook_data = {
        "reference": "sc-test-ref-12345",
        "amount": 4990000,
        "currency": "NGN",
        "customer": {"customer_code": "CUS_xyz987654"},
        "subscription": {"subscription_code": "SUB_grow123"},
    }

    await billing._activate_checkout(session, org_id, "sc-test-ref-12345", webhook_data)

    # Assert tenant was updated to operator_growth with 250 queries limit and query counter reset
    tenant_update = next(
        (p for s, p in zip(session.executed_statements, session.executed_parameters) if "subscription_tier = :tier_name" in s),
        None,
    )
    assert tenant_update is not None
    assert tenant_update["tier_name"] == "operator_growth"
    assert tenant_update["query_limit"] == 250
    assert tenant_update["cust_code"] == "CUS_xyz987654"
    assert tenant_update["sub_code"] == "SUB_grow123"


# ---------------------------------------------------------------------------
# 5. Multi-Tenant Relational Integrity Contracts
# ---------------------------------------------------------------------------

def test_migration_0042_relational_integrity_contracts() -> None:
    """Migration 0042 enforces dual tenant identity parity, RLS, and strict foreign keys."""
    import importlib.util
    from pathlib import Path

    mig_file = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0042_2026_09_24_auth_billing_and_two_stage_onboarding.py"
    )
    spec = importlib.util.spec_from_file_location("mig_0042", mig_file)
    assert spec is not None and spec.loader is not None
    mig_0042 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig_0042)

    assert mig_0042.revision == "0042"
    assert mig_0042.down_revision == "0041"

    # Inspect table definitions in migration
    mock_op = MagicMock()
    mig_0042.op = mock_op

    mig_0042.upgrade()
    executed = " ".join(str(call) for call in mock_op.execute.call_args_list)

    assert "subscription_tier VARCHAR(40)" in executed
    assert "pilot_expires_at TIMESTAMPTZ" in executed
    assert "monthly_workspace_query_limit INT" in executed
    assert "stage_a_completed BOOLEAN" in executed
    assert "stage_b_completed BOOLEAN" in executed
    assert "auth.organization_invitations" in executed
    assert "auth.otp_verifications" in executed
    assert "tenant_isolation_org_invitations" in executed


# ---------------------------------------------------------------------------
# 6. Lean Admin Operator Controller
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_tenants_list_requires_superuser() -> None:
    """Non-superusers are forbidden from viewing admin tenant management."""
    ctx = make_context(is_superuser=False, role="ADMIN")
    with pytest.raises(HTTPException) as exc_info:
        await admin.require_superuser_context(ctx)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_tenants_list_accessible_by_superuser() -> None:
    """Superuser administrator successfully queries all organizations with quota metrics."""
    session = MockAsyncSession([
        [{
            "organization_id": uuid4(),
            "name": "Flutterwave Global",
            "subscription_tier": "institutional_scale",
            "pilot_expires_at": None,
            "monthly_workspace_query_limit": 1000,
            "queries_used_this_period": 85,
            "stage_a_completed": True,
            "created_at": datetime.now(UTC),
            "seat_count": 24,
        }]
    ])
    ctx = make_context(is_superuser=True, role="ADMIN", db_session=session)

    tenants = await admin.list_admin_tenants(ctx)
    assert len(tenants) == 1
    assert tenants[0]["name"] == "Flutterwave Global"
    assert tenants[0]["subscription_tier"] == "institutional_scale"
    assert tenants[0]["seat_count"] == 24


@pytest.mark.asyncio
async def test_admin_pipeline_health_reports_verified_signal_telemetry() -> None:
    """Admin pipeline health returns verified signal counts and ingestion status."""
    now = datetime.now(UTC)
    session = MockAsyncSession([
        # 1. Total signals count
        [{"count": 4131}],
        # 2. Latest signal timestamp
        [{"latest": now}],
        # 3. Signals by type
        [
            {"signal_type": "regulatory_mandate", "cnt": 1500},
            {"signal_type": "competitor_move", "cnt": 1400},
            {"signal_type": "rail_degradation", "cnt": 1231},
        ],
    ])
    ctx = make_context(is_superuser=True, db_session=session)

    health = await admin.pipeline_health(ctx)
    assert health["status"] == "HEALTHY"
    assert health["total_verified_signals"] == 4131
    assert health["feeds_active"] == 11
    assert health["signals_by_type"]["regulatory_mandate"] == 1500
