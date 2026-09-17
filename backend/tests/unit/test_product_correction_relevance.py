"""Strong applicability is required before urgency or geography can rank news."""

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from app.decision import ContextObject, DecisionLens, FocusArea, assess_relevance
from app.decision import calculate_personal_priority
from tests.unit.test_decision_engine import _assessment


def test_country_only_cannot_create_monitoring_or_a_decision():
    _, values, _ = _assessment()
    country = ContextObject(uuid4(), "MARKET", "Nigeria", uuid4(), "CRITICAL")
    values = replace(
        values, context_objects=(country,), signal_entity_ids=frozenset({country.entity_id}),
        evidence_text="An unrelated telecom network launched in Nigeria.",
        urgency_score=Decimal("1"), strategic_priorities=frozenset(),
        rules=(replace(values.rules[0], conditions={"event_types": [values.event_type]}),),
    )
    result = assess_relevance(values)
    assert result.relevance_score < Decimal("0.450")
    assert not result.decision_required
    assert not result.meaningful_relevance
    assert result.decision_posture == "NO_ACTION"
    assert not result.matched_objects


@pytest.mark.parametrize("kind", ["COMPETITOR", "DEPENDENCY", "PRODUCT"])
def test_supported_company_match_remains_meaningful(kind):
    _, values, _ = _assessment()
    values = replace(values, context_objects=(replace(values.context_objects[0], object_type=kind),))
    result = assess_relevance(values)
    assert result.meaningful_relevance
    assert result.relevance_score >= Decimal("0.450")
    assert result.matched_objects[0].name == "CloudRail"
    assert "CloudRail" in result.why_relevant


@pytest.mark.parametrize("label", ["", "  ", "Rail"])
def test_empty_or_partial_entity_names_do_not_match(label):
    _, values, _ = _assessment()
    values = replace(
        values, context_objects=(ContextObject(uuid4(), "DEPENDENCY", label, None, "HIGH"),),
        strategic_priorities=frozenset(),
    )
    assert not assess_relevance(values).meaningful_relevance


def test_supported_strategic_priority_can_establish_relevance():
    _, values, _ = _assessment()
    values = replace(values, context_objects=(), strategic_priorities=frozenset({"settlement reliability"}),
                     evidence_text="The development affects settlement reliability.")
    result = assess_relevance(values)
    assert result.meaningful_relevance
    assert result.matched_strategic_priorities == ("settlement reliability",)
    assert result.relevance_score >= Decimal("0.450")
    assert "settlement reliability" in result.why_relevant


def test_nonmatching_company_remains_no_action():
    _, values, _ = _assessment()
    values = replace(values, context_objects=(), operating_markets=frozenset({"NO"}),
                     strategic_priorities=frozenset({"Norwegian merchant acquiring"}))
    result = assess_relevance(values)
    assert not result.meaningful_relevance
    assert result.decision_posture == "NO_ACTION"
    assert not result.decision_required


def test_focus_area_matching_rejects_country_blank_and_substrings():
    assessment, values, _ = _assessment()
    lens = DecisionLens("CFO", frozenset(), frozenset(), "ALL", 1)
    priority = calculate_personal_priority(
        assessment, lens,
        (FocusArea("Nigeria", "MARKET", None, Decimal(1)),
         FocusArea("", "TOPIC", None, Decimal(1)),
         FocusArea("Rail", "TOPIC", None, Decimal(1)),
         FocusArea("CloudRail", "TOPIC", None, Decimal(1))),
        values.primary_domain, values.event_type, values.signal_entity_ids, values.evidence_text,
    )
    assert priority.focus_matches == ("CloudRail",)


def test_geography_typed_as_a_priority_still_cannot_establish_relevance():
    _, values, _ = _assessment()
    result = assess_relevance(replace(values, context_objects=(),
                                     strategic_priorities=frozenset({"Nigeria", "NG", ""})))
    assert not result.meaningful_relevance


def test_cfo_responsibilities_establish_supported_personal_relevance():
    _, values, _ = _assessment()
    evidence = "Nigerian payment providers face increased settlement fees."
    assessment = assess_relevance(replace(values, context_objects=(), evidence_text=evidence,
                                         strategic_priorities=frozenset()))
    cfo = calculate_personal_priority(assessment, DecisionLens("CFO", frozenset(), frozenset(), "ALL", 1),
                                     (), values.primary_domain, values.event_type, frozenset(), evidence)
    coo = calculate_personal_priority(assessment, DecisionLens("COO", frozenset(), frozenset(), "ALL", 1),
                                     (), values.primary_domain, values.event_type, frozenset(), evidence)
    assert cfo.score >= Decimal("0.450")
    assert cfo.relevance_trace["matched_role_concerns"] == ["settlement economics"]
    assert "CFO" in cfo.relevance_trace["why_relevant"]
    assert coo.score == 0
    assert coo.relevance_trace["decision_posture"] == "NO_ACTION"
    assert not assessment.decision_required


def test_explicit_focus_can_establish_personal_monitoring_without_company_object():
    _, values, _ = _assessment()
    evidence = "Moniepoint introduced a merchant service in Nigeria."
    assessment = assess_relevance(replace(values, context_objects=(), evidence_text=evidence,
                                         strategic_priorities=frozenset()))
    lens = DecisionLens("CFO", frozenset(), frozenset(), "ALL", 1)
    priority = calculate_personal_priority(assessment, lens,
        (FocusArea("Moniepoint", "TOPIC", None, Decimal(1)),), values.primary_domain,
        values.event_type, frozenset(), evidence)
    assert priority.score >= Decimal("0.450")
    assert priority.relevance_trace["matched_focus_areas"] == ["Moniepoint"]
    assert priority.relevance_trace["decision_posture"] == "MONITOR"


def test_role_and_focus_do_not_make_an_unrelated_market_personal():
    _, values, _ = _assessment()
    evidence = "Settlement fees changed in an unrelated market."
    assessment = assess_relevance(replace(values, context_objects=(), evidence_text=evidence,
        operating_markets=frozenset({"NO"}), strategic_priorities=frozenset()))
    lens = DecisionLens("CFO", frozenset(), frozenset({values.primary_domain}), "ALL", 1)
    priority = calculate_personal_priority(assessment, lens, (), values.primary_domain,
                                         values.event_type, frozenset(), evidence)
    assert priority.score == 0
    assert priority.relevance_trace["decision_posture"] == "NO_ACTION"
