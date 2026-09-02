from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.auth import Principal, RequestContext
from app.api.v1 import admin


class Result:
    def __init__(self, *, row=None, rows=None, scalar=None) -> None:
        self.row = row
        self.rows = [] if rows is None else rows
        self.scalar = scalar

    def mappings(self) -> "Result":
        return self

    def one(self):
        assert self.row is not None
        return self.row

    def one_or_none(self):
        return self.row

    def all(self):
        return self.rows

    def scalar_one(self):
        assert self.scalar is not None
        return self.scalar

    def scalar_one_or_none(self):
        return self.scalar


class Session:
    def __init__(self, *results: Result) -> None:
        self.results = list(results)
        self.statements: list[str] = []
        self.parameters: list[dict | None] = []
        self.commits = 0

    async def execute(self, statement, parameters=None) -> Result:
        self.statements.append(str(statement))
        self.parameters.append(parameters)
        assert self.results, f"Unexpected SQL execution: {statement}"
        return self.results.pop(0)

    async def commit(self) -> None:
        self.commits += 1


def system_context(session: Session, *, role: str = "SYSTEM_ADMIN", methods=("mfa",)) -> RequestContext:
    principal = Principal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        permission_role=role,
        permissions=frozenset({"SYSTEM_ADMIN"}),
        authentication_methods=frozenset(methods),
    )
    return RequestContext(principal=principal, session=session)  # type: ignore[arg-type]


def detail_results(tenant_id, **overrides) -> list[Result]:
    row = {
        "id": tenant_id,
        "name": "Acme",
        "status": "ACTIVE",
        "started_at": datetime.now(UTC),
        "profile_completeness": 1,
        "operating_markets": ["Nigeria"],
        "object_count": 2,
        "resolved_count": 2,
        "company_briefs": 1,
        "monitoring_count": 3,
        "pending_invites": 1,
        "accepted_invites": 1,
        "lens_count": 1,
        "focus_count": 1,
        **overrides,
    }
    return [Result(row=row), *(Result(rows=[]) for _ in range(5))]


@pytest.mark.asyncio
async def test_system_admin_boundary_requires_role_and_mfa() -> None:
    with pytest.raises(HTTPException, match="System administrator"):
        await admin.get_system_admin_context(system_context(Session(), role="ADMIN"))
    with pytest.raises(HTTPException, match="Multi-factor"):
        await admin.get_system_admin_context(system_context(Session(), methods=()))

    session = Session(Result())
    context = system_context(session)
    assert await admin.get_system_admin_context(context) is context
    assert "app.system_admin" in session.statements[0]


def test_admin_payloads_normalise_and_validate_operator_input() -> None:
    body = admin.TenantProvisionInput(
        canonical_company_name="Acme Ltd",
        company_website="https://acme.example",
        business_categories=[" Fintech ", "Fintech"],
        markets=[" Nigeria  ", "Nigeria"],
        products=[" Payments "],
        pilot_owner="Stem Operator",
    )
    assert body.business_categories == ["Fintech"]
    assert body.markets == ["Nigeria"]
    assert admin.InvitationCreateInput(email=" User@Example.COM ").email == "user@example.com"
    with pytest.raises(ValidationError):
        admin.InvitationCreateInput(email="not-an-email")
    assert admin._slug("  Acme & Co.  ", uuid4()).startswith("acme-co-")


@pytest.mark.asyncio
async def test_create_and_patch_tenant_return_readiness_detail() -> None:
    body = admin.TenantProvisionInput(
        canonical_company_name="Acme Ltd",
        company_website="https://acme.example",
        business_categories=["Fintech"],
        markets=["Nigeria"],
        products=["Payments"],
        dependencies=["NIBSS"],
        competitors=["Peer Bank"],
        pilot_owner="Stem Operator",
    )
    create_session = Session(
        *(Result() for _ in range(8)),
        *detail_results(uuid4()),
    )
    created = await admin.create_tenant(body, system_context(create_session))
    assert created["checklist"]["entities_resolved"] is True
    assert create_session.commits == 1
    assert sum("company_objects" in statement for statement in create_session.statements) >= 4
    object_parameters = [
        parameters
        for statement, parameters in zip(
            create_session.statements, create_session.parameters, strict=True
        )
        if "INSERT INTO context.company_objects" in statement
    ]
    assert [parameters["resolution_status"] for parameters in object_parameters] == [
        "NOT_APPLICABLE",
        "UNRESOLVED",
        "UNRESOLVED",
        "UNRESOLVED",
    ]
    assert all(
        "CASE WHEN" not in statement
        for statement in create_session.statements
        if "INSERT INTO context.company_objects" in statement
    )

    tenant_id = uuid4()
    patch_session = Session(Result(), Result(), Result(), *detail_results(tenant_id))
    patched = await admin.patch_tenant(
        tenant_id,
        admin.TenantPatchInput(
            canonical_company_name="Acme Holdings",
            tenant_status="ACTIVE",
            pilot_status="ACTIVE",
            pilot_owner="Operator Two",
        ),
        system_context(patch_session),
    )
    assert patched["tenant"]["name"] == "Acme"
    assert patch_session.commits == 1


@pytest.mark.asyncio
async def test_tenant_detail_lists_and_not_found_paths() -> None:
    tenant_id = uuid4()
    listed = await admin.list_tenants(system_context(Session(Result(rows=[{"id": tenant_id}]))))
    assert listed == [{"id": str(tenant_id)}]

    detail_session = Session(*detail_results(tenant_id))
    detail = await admin.get_tenant(tenant_id, system_context(detail_session))
    assert all(detail["checklist"].values())
    assert "resolution_status IN ('RESOLVED','NOT_APPLICABLE')" in detail_session.statements[0]
    with pytest.raises(HTTPException) as missing:
        await admin.get_tenant(tenant_id, system_context(Session(Result(row=None))))
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_invitation_create_and_revoke_are_audited(monkeypatch) -> None:
    tenant_id = uuid4()
    invitation_id = uuid4()
    monkeypatch.setattr(
        admin,
        "get_settings",
        lambda: SimpleNamespace(
            PHASE5_PILOT_INVITES_ENABLED=True,
            FRONTEND_PUBLIC_URL="https://app.staging.stem-cogent.com/",
        ),
    )
    session = Session(Result(scalar=1), Result(), Result(scalar=invitation_id), Result())
    created = await admin.create_invitation(
        tenant_id,
        admin.InvitationCreateInput(email="pilot@example.com"),
        system_context(session),
    )
    assert created["id"] == invitation_id
    assert created["invitation_url"].startswith("https://app.staging.stem-cogent.com/invite/accept?token=")
    assert session.commits == 1

    revoke_session = Session(Result(row={"tenant_id": tenant_id}), Result())
    assert await admin.revoke_invitation(invitation_id, system_context(revoke_session)) == {"status": "REVOKED"}
    with pytest.raises(HTTPException) as missing:
        await admin.revoke_invitation(invitation_id, system_context(Session(Result(row=None))))
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_activation_dispatch_and_status_views(monkeypatch) -> None:
    tenant_id = uuid4()
    run_id = uuid4()
    sent: dict = {}
    monkeypatch.setattr(
        admin,
        "get_settings",
        lambda: SimpleNamespace(
            PHASE5_FIRST_VALUE_ACTIVATION_ENABLED=True,
            SQS_PIPELINE_SYNTHESIZED_URL="https://sqs.example/activation-queue",
        ),
    )
    monkeypatch.setattr(admin.celery_app, "send_task", lambda *args, **kwargs: sent.update(args=args, kwargs=kwargs))
    session = Session(Result(scalar=3), Result(scalar=run_id), Result())
    queued = await admin.start_activation(
        tenant_id,
        admin.ActivationCreateInput(lookback_days=45),
        system_context(session),
    )
    assert queued == {"id": run_id, "status": "QUEUED"}
    assert sent["kwargs"]["queue"] == "activation-queue"

    rows = [{"id": run_id, "status": "COMPLETED"}]
    assert (await admin.tenant_activation(tenant_id, system_context(Session(Result(rows=rows)))))[0]["id"] == str(run_id)
    assert (await admin.activation_run(run_id, system_context(Session(Result(row=rows[0])))))["status"] == "COMPLETED"
    with pytest.raises(HTTPException):
        await admin.activation_run(run_id, system_context(Session(Result(row=None))))


@pytest.mark.asyncio
async def test_entity_review_pipeline_and_metrics_paths() -> None:
    tenant_id = uuid4()
    object_id = uuid4()
    entity_id = uuid4()
    queue = await admin.entity_review_queue(
        10,
        system_context(Session(Result(rows=[{"id": object_id, "name": "NIBSS"}]))),
    )
    assert queue[0]["id"] == str(object_id)

    resolve_session = Session(
        Result(row={"id": object_id, "tenant_id": tenant_id}),
        Result(scalar=entity_id),
        Result(row={"id": object_id, "entity_id": entity_id, "resolution_status": "RESOLVED"}),
        Result(),
    )
    resolved = await admin.resolve_entity_review(
        object_id,
        admin.EntityReviewInput(action="CREATE", canonical_name="NIBSS", entity_type="COMPANY"),
        system_context(resolve_session),
    )
    assert resolved["resolution_status"] == "RESOLVED"

    registry_id = uuid4()
    audit_session = Session(
        Result(rows=[{"id": registry_id, "canonical_name": "Nigeria Inter-Bank Settlement System", "aliases": ["NIBSS"]}]),
        Result(rows=[{"id": object_id, "object_type": "DEPENDENCY", "name": "NIBSS"}]),
        Result(),
    )
    counts = await admin.audit_tenant_entities(tenant_id, system_context(audit_session))
    assert counts["RESOLVED"] == 1

    pipeline = await admin.pipeline_status(
        system_context(Session(Result(row={"active_sources": 4, "failed_jobs": 0})))
    )
    assert pipeline["active_sources"] == 4

    started = datetime.now(UTC) - timedelta(hours=2)
    metrics_row = {
        "started_at": started,
        "first_useful_brief_available_at": started + timedelta(minutes=30),
        "briefs_created": 4,
        "briefs_opened": 2,
        "acknowledged": 1,
        "escalated": 1,
        "acted_on": 0,
        "dismissed": 0,
    }
    metrics = await admin.tenant_pilot_metrics(
        tenant_id,
        system_context(Session(Result(row=metrics_row))),
    )
    assert metrics["time_to_first_value_seconds"] == 1800
    assert metrics["brief_open_rate"] == 0.5
    assert metrics["action_rate"] == 1.0
