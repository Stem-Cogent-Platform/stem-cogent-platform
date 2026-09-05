from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api import auth
from app.api.auth import Principal, RequestContext
from app.api.v1 import cil, context, reviews
from app.cil.retrieval import CILCitation, CILRetrievalResult
from app.compliance.documents import current_legal_documents
from app.context import cache


class FakeResult:
    def __init__(
        self,
        *,
        one=None,
        one_or_none=None,
        all_rows=None,
        scalar_one=None,
        scalar_one_or_none=None,
    ) -> None:
        self._one = one
        self._one_or_none = one_or_none
        self._all = [] if all_rows is None else all_rows
        self._scalar_one = scalar_one
        self._scalar_one_or_none = scalar_one_or_none

    def mappings(self) -> "FakeResult":
        return self

    def one(self):
        return self._one

    def one_or_none(self):
        return self._one_or_none

    def all(self):
        return self._all

    def scalar_one(self):
        return self._scalar_one

    def scalar_one_or_none(self):
        return self._scalar_one_or_none


class FakeSession:
    def __init__(self, *results: FakeResult) -> None:
        self.results = list(results)
        self.statements: list[str] = []
        self.commits = 0

    async def execute(self, statement, parameters=None) -> FakeResult:
        self.statements.append(str(statement))
        assert self.results, f"Unexpected SQL execution: {statement}"
        return self.results.pop(0)

    async def commit(self) -> None:
        self.commits += 1


def make_context(
    session: FakeSession, *permissions: str, accepted: bool = True
) -> RequestContext:
    accepted_at = datetime.now(UTC) if accepted else None
    legal = current_legal_documents()
    principal = Principal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        permission_role="CEO",
        permissions=frozenset(permissions),
        tos_accepted_at=accepted_at,
        tos_version=legal["terms"].version if accepted else None,
        privacy_policy_accepted_at=accepted_at,
        privacy_policy_version=legal["privacy"].version if accepted else None,
        ndpa_consent_accepted_at=accepted_at,
        ndpa_consent_version=legal["ndpa"].version if accepted else None,
        binding_app_version="0.1.0" if accepted else None,
        current_compliance_ledger_id=uuid4() if accepted else None,
        plan_code="TRIAL",
        billing_status="TRIALING",
        entitlements={"cil": True, "realtime_briefing": True},
    )
    return RequestContext(principal=principal, session=session)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_context_api_happy_paths_use_tenant_scoped_bound_queries(monkeypatch) -> None:
    row_id = uuid4()
    row = {"id": row_id, "name": "Payments", "active": True}
    session = FakeSession(
        FakeResult(one_or_none=row),
        FakeResult(all_rows=[row]),
        FakeResult(one=row),
        FakeResult(),
        FakeResult(one=row),
        FakeResult(),
        FakeResult(one_or_none=row),
        FakeResult(),
        FakeResult(one_or_none=row),
        FakeResult(one=row),
        FakeResult(),
        FakeResult(all_rows=[row]),
        FakeResult(one=row),
        FakeResult(),
        FakeResult(one_or_none=row),
        FakeResult(),
        FakeResult(scalar_one_or_none=row_id),
        FakeResult(),
    )
    request_context = make_context(
        session,
        "CONFIGURE_COMPANY_CONTEXT",
        "CONFIGURE_DECISION_LENS",
        "CONFIGURE_FOCUS_AREAS",
    )
    monkeypatch.setattr(context, "cache_get", AsyncMock(return_value=None))
    monkeypatch.setattr(context, "cache_set", AsyncMock())
    monkeypatch.setattr(context, "invalidate_company", AsyncMock())
    monkeypatch.setattr(context, "invalidate_user", AsyncMock())

    company = await context.get_company_context(request_context)
    assert company["profile"]["id"] == str(row_id)

    await context.put_company_context(
        context.CompanyProfileInput(
            business_categories=["FINTECH"],
            operating_markets=["NG"],
            strategic_priorities=["GROWTH"],
        ),
        request_context,
    )
    await context.create_company_object(
        context.CompanyObjectInput(object_type="PRODUCT", name="Payments"),
        request_context,
    )
    await context.patch_company_object(
        row_id,
        context.CompanyObjectPatch(name="Collections", metadata={"tier": 1}),
        request_context,
    )
    assert "SET name = :name, metadata = CAST(:metadata AS JSONB)" in session.statements[6]

    assert await context.get_decision_lens(request_context) is not None
    await context.put_decision_lens(
        context.DecisionLensInput(role_code="CEO", priority_domains=["REGULATORY_POLICY"]),
        request_context,
    )
    assert len(await context.get_focus_areas(request_context)) == 1
    await context.create_focus_area(
        context.FocusAreaInput(focus_type="TOPIC", label="Payments"),
        request_context,
    )
    await context.patch_focus_area(
        row_id,
        context.FocusAreaPatch(label="Settlement", weight=0.8),
        request_context,
    )
    assert "SET label = :label, weight = :weight" in session.statements[14]
    response = await context.delete_focus_area(row_id, request_context)
    assert response.status_code == 204
    assert session.commits == 7
    assert not session.results


@pytest.mark.asyncio
async def test_context_api_validation_and_not_found_paths(monkeypatch) -> None:
    row_id = uuid4()
    allowed = make_context(
        FakeSession(FakeResult(one_or_none=None)),
        "CONFIGURE_COMPANY_CONTEXT",
        "CONFIGURE_FOCUS_AREAS",
    )
    monkeypatch.setattr(context, "invalidate_company", AsyncMock())

    with pytest.raises(HTTPException) as empty_patch:
        await context.patch_company_object(row_id, context.CompanyObjectPatch(), allowed)
    assert empty_patch.value.status_code == 422

    with pytest.raises(HTTPException) as missing_object:
        await context.patch_company_object(
            row_id, context.CompanyObjectPatch(active=False), allowed
        )
    assert missing_object.value.status_code == 404

    with pytest.raises(HTTPException) as entity_without_id:
        await context.create_focus_area(
            context.FocusAreaInput(focus_type="ENTITY", label="Bank"), allowed
        )
    assert entity_without_id.value.status_code == 422

    denied = make_context(FakeSession())
    with pytest.raises(HTTPException) as forbidden:
        await context.put_company_context(context.CompanyProfileInput(), denied)
    assert forbidden.value.status_code == 403


@pytest.mark.asyncio
async def test_company_context_cannot_bypass_legal_consent() -> None:
    unconsented = make_context(
        FakeSession(), "CONFIGURE_COMPANY_CONTEXT", accepted=False
    )
    with pytest.raises(HTTPException) as rejected:
        await context.put_company_context(
            context.CompanyProfileInput(
                business_categories=["PAYMENTS"],
                operating_markets=["NG"],
                strategic_priorities=["SETTLEMENT_RESILIENCE"],
            ),
            unconsented,
        )
    assert rejected.value.status_code == 403
    assert rejected.value.detail["code"] == "LEGAL_CONSENT_REQUIRED"
    assert unconsented.session.statements == []


@pytest.mark.asyncio
async def test_context_api_cache_hits_and_focus_not_found_branches(monkeypatch) -> None:
    row_id = uuid4()
    cached_context = make_context(FakeSession())
    monkeypatch.setattr(
        context,
        "cache_get",
        AsyncMock(side_effect=[{"profile": "cached"}, {"role": "CEO"}, [{"label": "Risk"}]]),
    )
    assert (await context.get_company_context(cached_context))["profile"] == "cached"
    assert (await context.get_decision_lens(cached_context))["role"] == "CEO"
    assert (await context.get_focus_areas(cached_context))[0]["label"] == "Risk"

    allowed = make_context(
        FakeSession(
            FakeResult(one_or_none=None),
            FakeResult(one_or_none=None),
            FakeResult(scalar_one_or_none=None),
        ),
        "CONFIGURE_FOCUS_AREAS",
    )
    monkeypatch.setattr(context, "invalidate_user", AsyncMock())
    with pytest.raises(HTTPException) as empty_patch:
        await context.patch_focus_area(row_id, context.FocusAreaPatch(), allowed)
    assert empty_patch.value.status_code == 422
    with pytest.raises(HTTPException) as missing_patch:
        await context.patch_focus_area(
            row_id, context.FocusAreaPatch(active=False), allowed
        )
    assert missing_patch.value.status_code == 404
    with pytest.raises(HTTPException) as missing_delete:
        await context.delete_focus_area(row_id, allowed)
    assert missing_delete.value.status_code == 404


@pytest.mark.asyncio
async def test_review_api_create_list_resolve_and_not_found() -> None:
    case_id = uuid4()
    row = {"id": case_id, "status": "OPEN"}
    session = FakeSession(
        FakeResult(one=row),
        FakeResult(),
        FakeResult(all_rows=[row]),
        FakeResult(one_or_none={**row, "status": "RESOLVED"}),
        FakeResult(),
        FakeResult(one_or_none=None),
    )
    request_context = make_context(
        session, "READ_INTELLIGENCE", "CONFIGURE_COMPANY_CONTEXT"
    )
    payload = reviews.ReviewCaseInput(
        review_type="CLASSIFICATION",
        signal_id=uuid4(),
        idempotency_key=uuid4(),
        reason_code="WRONG_CLASS",
        observed_values={"domain": "OLD"},
        proposed_values={"domain": "NEW"},
    )
    assert (await reviews.create_review_case(payload, request_context))["id"] == case_id
    assert len(await reviews.list_review_cases("OPEN", request_context)) == 1
    resolved = await reviews.resolve_review_case(
        case_id,
        reviews.ReviewResolution(status="RESOLVED", resolution={"accepted": True}),
        request_context,
    )
    assert resolved["status"] == "RESOLVED"
    with pytest.raises(HTTPException) as missing:
        await reviews.resolve_review_case(
            uuid4(), reviews.ReviewResolution(status="IN_REVIEW"), request_context
        )
    assert missing.value.status_code == 404
    assert session.commits == 2


def test_review_payloads_require_their_subject_and_final_resolution() -> None:
    common = {"signal_id": uuid4(), "idempotency_key": uuid4(), "reason_code": "CHECK"}
    with pytest.raises(ValueError, match="entity_id"):
        reviews.ReviewCaseInput(review_type="ENTITY_RESOLUTION", **common)
    with pytest.raises(ValueError, match="brief_id"):
        reviews.ReviewCaseInput(review_type="DECISION_RELEVANCE", **common)
    with pytest.raises(ValueError, match="final resolution"):
        reviews.ReviewResolution(status="REJECTED")


@pytest.mark.asyncio
async def test_cil_query_creates_and_reuses_grounded_sessions(monkeypatch) -> None:
    session_id = uuid4()
    signal_id = uuid4()
    result = CILRetrievalResult(
        structured_context={"signal": {"id": str(signal_id)}},
        citations=(CILCitation(signal_id, "CBN", "https://cbn.gov.ng/source"),),
        retrieved_signal_ids=(signal_id,),
        retrieved_global_output_ids=(),
        retrieved_brief_ids=(),
        confidence_indicator="HIGH",
    )
    monkeypatch.setattr(cil, "retrieve_context", AsyncMock(return_value=result))
    monkeypatch.setattr(
        cil,
        "get_settings",
        lambda: SimpleNamespace(PHASE5_PRODUCT_ANALYTICS_ENABLED=True),
    )
    session = FakeSession(
        FakeResult(scalar_one=session_id),
        FakeResult(),
        FakeResult(),
        FakeResult(),
        FakeResult(scalar_one_or_none=session_id),
        FakeResult(),
        FakeResult(),
        FakeResult(),
    )
    request_context = make_context(session, "USE_CIL")
    first = await cil.query_cil(
        cil.CILQuery(query="What changed?", anchor_type="SIGNAL", anchor_id=signal_id),
        request_context,
    )
    assert first.response_grounded is True
    assert first.citations[0]["source_name"] == "CBN"
    second = await cil.query_cil(
        cil.CILQuery(
            query="What matters?",
            anchor_type="SIGNAL",
            anchor_id=signal_id,
            session_id=session_id,
        ),
        request_context,
    )
    assert second.session_id == session_id
    assert session.commits == 2
    audit_statements = [
        statement for statement in session.statements
        if "CIL_QUERY_SUBMITTED" in statement
    ]
    assert audit_statements
    assert all("CAST(:grounded AS BOOLEAN)" in statement for statement in audit_statements)


@pytest.mark.asyncio
async def test_cil_missing_session_and_ungrounded_response(monkeypatch) -> None:
    result = CILRetrievalResult({}, (), (), (), (), "INSUFFICIENT_DATA")
    monkeypatch.setattr(cil, "retrieve_context", AsyncMock(return_value=result))
    missing_context = make_context(
        FakeSession(FakeResult(scalar_one_or_none=None)), "USE_CIL"
    )
    payload = cil.CILQuery(
        query="What changed?",
        anchor_type="DECISION_BRIEF",
        anchor_id=uuid4(),
        session_id=uuid4(),
    )
    with pytest.raises(HTTPException) as missing:
        await cil.query_cil(payload, missing_context)
    assert missing.value.status_code == 404

    new_id = uuid4()
    fresh_context = make_context(
        FakeSession(FakeResult(scalar_one=new_id), FakeResult(), FakeResult()), "USE_CIL"
    )
    response = await cil.query_cil(
        payload.model_copy(update={"session_id": None}), fresh_context
    )
    assert response.response_grounded is False
    assert response.follow_up_suggestions == []


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def test_auth_token_verification_and_permissions(monkeypatch) -> None:
    secret = "production-test-secret"
    header = _encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = _encode(
        json.dumps({"sub": str(uuid4()), "tenant_id": str(uuid4()), "exp": time.time() + 60}).encode()
    )
    signature = _encode(hmac.new(secret.encode(), f"{header}.{claims}".encode(), hashlib.sha256).digest())
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(JWT_SIGNING_SECRET_ARN="arn:test"))
    monkeypatch.setattr(auth, "get_secret_string", lambda _arn: secret)

    assert auth._verify_hs256_token(f"{header}.{claims}.{signature}")["sub"]
    with pytest.raises(HTTPException, match="Invalid token signature"):
        auth._verify_hs256_token(f"{header}.{claims}.{_encode(b'bad')}")
    with pytest.raises(HTTPException, match="Malformed bearer token"):
        auth._verify_hs256_token("not-a-token")
    with pytest.raises(HTTPException, match="Missing permission"):
        auth.require_permission(make_context(FakeSession()), "USE_CIL")


@pytest.mark.asyncio
async def test_context_cache_success_fallback_and_invalidation(monkeypatch) -> None:
    monkeypatch.setattr(cache, "get_redis_client", lambda: None)
    assert await cache.cache_get("missing") is None
    await cache.cache_set("missing", {"ignored": True})
    await cache.invalidate_company(uuid4())

    client = SimpleNamespace(
        get=AsyncMock(return_value=json.dumps({"cached": True})),
        set=AsyncMock(),
        delete=AsyncMock(),
        publish=AsyncMock(),
    )
    monkeypatch.setattr(cache, "get_redis_client", lambda: client)
    assert await cache.cache_get("company") == {"cached": True}
    await cache.cache_set("company", {"id": uuid4()})
    tenant_id, user_id = uuid4(), uuid4()
    await cache.invalidate_user(tenant_id, user_id)
    client.set.assert_awaited_once()
    client.delete.assert_awaited_once_with(
        f"context:lens:{tenant_id}:{user_id}",
        f"context:focus:{tenant_id}:{user_id}",
    )
    client.publish.assert_awaited_once()

    client.get.side_effect = RuntimeError("redis unavailable")
    client.set.side_effect = RuntimeError("redis unavailable")
    client.delete.side_effect = RuntimeError("redis unavailable")
    assert await cache.cache_get("company") is None
    await cache.cache_set("company", {})
    await cache.invalidate_company(tenant_id)


def test_auth_rejects_unavailable_unsupported_and_expired_tokens(monkeypatch) -> None:
    secret = "production-test-secret"

    def token(header_value: dict, claims_value: dict) -> str:
        header = _encode(json.dumps(header_value).encode())
        claims = _encode(json.dumps(claims_value).encode())
        signature = _encode(
            hmac.new(
                secret.encode(), f"{header}.{claims}".encode(), hashlib.sha256
            ).digest()
        )
        return f"{header}.{claims}.{signature}"

    claims = {"sub": str(uuid4()), "tenant_id": str(uuid4()), "exp": time.time() + 60}
    valid = token({"alg": "HS256", "typ": "JWT"}, claims)
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(JWT_SIGNING_SECRET_ARN=""))
    with pytest.raises(HTTPException, match="verifier is unavailable"):
        auth._verify_hs256_token(valid)

    monkeypatch.setattr(
        auth, "get_settings", lambda: SimpleNamespace(JWT_SIGNING_SECRET_ARN="arn:test")
    )
    monkeypatch.setattr(auth, "get_secret_string", lambda _arn: secret)
    with pytest.raises(HTTPException, match="Unsupported bearer token"):
        auth._verify_hs256_token(token({"alg": "none"}, claims))
    with pytest.raises(HTTPException, match="Expired bearer token"):
        auth._verify_hs256_token(
            token(
                {"alg": "HS256", "typ": "JWT"},
                {**claims, "exp": time.time() - 1},
            )
        )
    with pytest.raises(HTTPException, match="Malformed bearer token"):
        auth._verify_hs256_token("e30.not-json.signature")
