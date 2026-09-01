from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.auth import Principal, RequestContext
from app.api.v1 import product
from app.compliance.documents import current_legal_documents


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

    def scalar_one_or_none(self):
        return self.scalar


class Session:
    def __init__(self, *results: Result) -> None:
        self.results = list(results)
        self.statements: list[str] = []
        self.commits = 0

    async def execute(self, statement, parameters=None) -> Result:
        self.statements.append(str(statement))
        assert self.results, f"Unexpected SQL execution: {statement}"
        return self.results.pop(0)

    async def commit(self) -> None:
        self.commits += 1


def context(session: Session) -> RequestContext:
    legal = current_legal_documents()
    accepted_at = datetime.now(UTC)
    principal = Principal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        permission_role="CEO",
        permissions=frozenset(
            {
                "READ_DECISION_BRIEFS",
                "ACT_ON_DECISION_BRIEF",
                "READ_INTELLIGENCE",
                "CONFIGURE_ALERTS",
                "CONFIGURE_COMPANY_CONTEXT",
                "MANAGE_USERS",
            }
        ),
        tos_accepted_at=accepted_at,
        tos_version=legal["terms"].version,
        privacy_policy_accepted_at=accepted_at,
        privacy_policy_version=legal["privacy"].version,
        ndpa_consent_accepted_at=accepted_at,
        ndpa_consent_version=legal["ndpa"].version,
        binding_app_version="0.1.0",
        current_compliance_ledger_id=uuid4(),
        plan_code="BUSINESS",
        billing_status="ACTIVE",
        entitlements={"company_intelligence_matrix": True},
    )
    return RequestContext(principal=principal, session=session)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_brief_listing_detail_and_action_paths() -> None:
    brief_id = uuid4()
    row = {"id": brief_id, "evidence_signal_ids": [uuid4()], "brief_status": "NEW"}

    listing_session = Session(Result(rows=[row]))
    listing = context(listing_session)
    assert (await product.list_briefs(None, 20, listing))[0]["id"] == str(brief_id)
    assert "CAST(:status_filter AS VARCHAR) IS NULL" in listing_session.statements[0]

    detail_session = Session(
        Result(row=row),
        Result(rows=[{"id": row["evidence_signal_ids"][0], "source_name": "CBN"}]),
        Result(rows=[{"id": uuid4(), "action_type": "WATCHING"}]),
        Result(rows=[{"event_type": "BRIEF_CREATED"}]),
        Result(),
    )
    detail = await product.get_brief(brief_id, context(detail_session))
    assert detail["evidence"][0]["source_name"] == "CBN"
    assert detail["actions"][0]["action_type"] == "WATCHING"
    assert detail_session.commits == 1

    action_id = uuid4()
    action_session = Session(
        Result(row={"id": action_id, "action_type": "ACKNOWLEDGED"}),
        Result(),
        Result(),
        Result(),
    )
    action = await product.record_decision_action(
        brief_id,
        product.DecisionActionInput(action_type="ACKNOWLEDGED", note="Reviewed"),
        context(action_session),
    )
    assert action["id"] == str(action_id)
    assert "brief_status" in action_session.statements[1]
    assert action_session.commits == 1

    missing = context(Session(Result(row=None)))
    with pytest.raises(HTTPException) as rejected:
        await product.get_brief(uuid4(), missing)
    assert rejected.value.status_code == 404


@pytest.mark.asyncio
async def test_company_intelligence_entity_and_alert_paths() -> None:
    company = context(Session(Result(row={"name": "Stem"}), Result(rows=[{"id": uuid4(), "evidence_signal_ids": [uuid4()]}])))
    assert (await product.company_lens(company))["profile"]["name"] == "Stem"

    intelligence_session = Session(Result(rows=[{"id": uuid4(), "summary": "Change", "citations": [{"source_signal_id": str(uuid4())}]}]))
    intelligence = context(intelligence_session)
    assert (await product.wider_intelligence(12, intelligence))[0]["summary"] == "Change"
    assert "source.source_name AS source_name" in intelligence_session.statements[0]

    entity_id = uuid4()
    entity = context(
        Session(
            Result(row={"id": entity_id, "canonical_name": "CBN"}),
            Result(rows=[{"id": uuid4(), "title": "Circular"}]),
            Result(rows=[{"relationship_type": "REGULATES"}]),
        )
    )
    profile = await product.entity_profile(entity_id, entity)
    assert profile["entity"]["canonical_name"] == "CBN"
    assert profile["relationships"][0]["relationship_type"] == "REGULATES"

    missing_entity = context(Session(Result(row=None)))
    with pytest.raises(HTTPException) as rejected:
        await product.entity_profile(uuid4(), missing_entity)
    assert rejected.value.status_code == 404

    watchlist = await product.watchlist(
        context(
            Session(
                Result(rows=[{"id": uuid4(), "name": "NIBSS", "recent_activity_count": 2}]),
                Result(rows=[{"id": uuid4(), "label": "Settlement", "recent_activity_count": None}]),
            )
        )
    )
    assert watchlist["company"][0]["recent_activity_count"] == 2
    assert watchlist["focus"][0]["label"] == "Settlement"

    alert_id = uuid4()
    alerts = context(Session(Result(rows=[{"id": alert_id, "status": "PENDING"}])))
    assert (await product.list_alerts(alerts))[0]["status"] == "PENDING"

    read_session = Session(Result(row={"id": alert_id, "status": "READ"}))
    assert (await product.read_alert(alert_id, context(read_session)))["status"] == "READ"
    assert read_session.commits == 1

    with pytest.raises(HTTPException) as rejected_alert:
        await product.read_alert(uuid4(), context(Session(Result(row=None))))
    assert rejected_alert.value.status_code == 404


@pytest.mark.asyncio
async def test_preferences_digests_and_complete_pilot_lifecycle() -> None:
    default_preferences = await product.get_alert_preferences(context(Session(Result(row=None))))
    assert default_preferences["delivery_channels"] == ["IN_APP"]

    preference_row = {
        "domain_codes": ["REGULATORY_POLICY"],
        "urgency_bands": ["HIGH"],
        "delivery_channels": ["IN_APP", "EMAIL"],
        "minimum_relevance_band": "MEDIUM",
        "digest_frequency": "DAILY",
        "enabled": True,
    }
    existing = await product.get_alert_preferences(context(Session(Result(row=preference_row))))
    assert existing["domain_codes"] == ["REGULATORY_POLICY"]

    update_session = Session(Result(row=preference_row))
    updated = await product.put_alert_preferences(
        product.AlertPreferencesInput(**preference_row), context(update_session)
    )
    assert updated["enabled"] is True
    assert update_session.commits == 1

    digests = context(Session(Result(rows=[{"id": uuid4(), "period_type": "DAILY"}])))
    assert (await product.list_digests(digests))[0]["period_type"] == "DAILY"

    not_started = await product.pilot_status(context(Session(Result(row=None))))
    assert not_started["status"] == "NOT_STARTED"

    engagement_id = uuid4()
    engagement = {"id": engagement_id, "status": "ACTIVE"}
    status_context = context(
        Session(
            Result(row=engagement),
            Result(rows=[{"day_number": 7, "status": "PENDING"}]),
            Result(rows=[{"event_type": "BRIEF_OPENED", "count": 3}]),
        )
    )
    pilot = await product.pilot_status(status_context)
    assert pilot["metrics"] == {"BRIEF_OPENED": 3}

    start_session = Session(Result(row=engagement), Result(), Result(), Result())
    started = await product.start_pilot(
        product.PilotStartInput(cohort_code="AUGUST-2026"), context(start_session)
    )
    assert started["status"] == "ACTIVE"
    assert start_session.commits == 1
    assert sum("pilot.checkpoints" in statement for statement in start_session.statements) == 3

    event_session = Session(Result(scalar=uuid4()))
    event = await product.record_pilot_event(
        product.PilotEventInput(
            event_type="VALUE_EXAMPLE",
            idempotency_key=uuid4(),
            properties={"brief": "useful"},
        ),
        context(event_session),
    )
    assert event == {"accepted": True}
    assert event_session.commits == 1

    checkpoint_session = Session(Result(row={"day_number": 7, "status": "COMPLETED"}))
    checkpoint = await product.complete_checkpoint(
        7,
        product.CheckpointInput(evidence={"notes": "Validated"}),
        context(checkpoint_session),
    )
    assert checkpoint["status"] == "COMPLETED"
    assert checkpoint_session.commits == 1

    with pytest.raises(HTTPException) as missing_checkpoint:
        await product.complete_checkpoint(
            14,
            product.CheckpointInput(evidence={}),
            context(Session(Result(row=None))),
        )
    assert missing_checkpoint.value.status_code == 404


@pytest.mark.asyncio
async def test_team_and_integration_settings_read_persisted_state() -> None:
    team = await product.list_team_members(
        context(Session(Result(rows=[{"id": uuid4(), "email": "owner@example.com"}])))
    )
    assert team[0]["email"] == "owner@example.com"

    integrations = await product.integration_status(
        context(Session(Result(rows=[{"id": uuid4(), "name": "Pilot key"}])))
    )
    assert integrations["api_keys"][0]["name"] == "Pilot key"
    assert integrations["plan_code"] == "BUSINESS"

