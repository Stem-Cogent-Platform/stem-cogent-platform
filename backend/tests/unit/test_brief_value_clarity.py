from dataclasses import replace
from uuid import uuid4

from app.decision import ContextObject, format_brief
from tests.unit.test_decision_engine import _assessment


def test_market_entry_review_names_the_configured_competitor_and_review_step():
    assessment, _, _ = _assessment()
    assessment = replace(
        assessment, decision_type="MARKET_ENTRY", owner_role_codes=("CEO", "PRODUCT"),
        matched_objects=(ContextObject(uuid4(), "COMPETITOR", "Grey", None, "HIGH"),),
    )
    headline = "Grey targets Africa-China trade with direct yuan payments"
    narrative = format_brief(headline, assessment, ("Grey",), "CEO")
    assert narrative.what_changed == headline
    assert "Grey is a competitor you track." in narrative.why_it_matters
    assert "market-entry plans" in narrative.decision_prompt
    assert "CEO, PRODUCT" in narrative.decision_prompt
    assert "cited evidence" in narrative.decision_prompt
    assert "MARKET_ENTRY" not in narrative.decision_prompt
    assert "must" not in narrative.decision_prompt
    assert narrative.uncertainties == assessment.uncertainty_codes


def test_monitoring_is_not_reworded_as_a_decision():
    assessment, _, _ = _assessment()
    narrative = format_brief("CloudRail reports an incident", replace(
        assessment, decision_required=False, decision_type=None,
    ))
    assert "CloudRail is a dependency" in narrative.why_it_matters
    assert narrative.decision_prompt == "Monitor this development; no decision is currently required."


def test_unknown_context_does_not_invent_a_competitor_or_dependency():
    assessment, _, _ = _assessment()
    narrative = format_brief("Source development", replace(assessment, matched_objects=()))
    assert narrative.why_it_matters == "No direct company object match was established."
