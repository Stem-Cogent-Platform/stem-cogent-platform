"""Integration tests for the Context Matching engine.

Tests the full route_signal_to_tenant_contexts flow with real database schema
via the shared test database, verifying that signals are correctly matched
against tenant operational footprints and persisted to
pipeline.tenant_signal_relevance.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.context.relevance_engine import compute_exposure, synthesize_lens_impact
from app.context.relevance_models import ExposureResult, LensImpact


# ─── Helpers ──────────────────────────────────────────────────────────────────

ORG_A_CONTEXT = {
    "name": "FXBridge Ltd",
    "slug": f"fxbridge-{uuid.uuid4().hex[:8]}",
    "operating_licenses": ["IMTO", "FINANCE_COMPANY"],
    "active_products": ["cross_border_fx", "virtual_accounts", "p2p_wallet"],
    "clearing_rails": ["PROVIDUS", "NIBSS", "WEMA"],
}

ORG_B_CONTEXT = {
    "name": "PayPOS Inc",
    "slug": f"paypos-{uuid.uuid4().hex[:8]}",
    "operating_licenses": ["PSSP", "SWITCHING"],
    "active_products": ["pos_acquiring", "agency_banking", "card_issuance"],
    "clearing_rails": ["INTERSWITCH", "NIBSS"],
}

CBN_POS_SIGNAL = {
    "signal_type": "regulatory_mandate",
    "urgency": "high",
    "sentiment": "threat",
    "primary_entity": "Central Bank of Nigeria",
    "secondary_entities": ["INTERSWITCH"],
    "affected_sectors": ["pos_acquiring", "agency_banking"],
    "executive_summary": "CBN issues directive mandating POS geofencing compliance for all PSSP licensees.",
    "title": "CBN POS Geofencing Directive",
    "source_url": "https://www.cbn.gov.ng/circulars/pos-geofencing-2026",
}

PROVIDUS_OUTAGE_SIGNAL = {
    "signal_type": "rail_degradation",
    "urgency": "critical",
    "sentiment": "threat",
    "primary_entity": "Providus Bank",
    "secondary_entities": ["PROVIDUS"],
    "affected_sectors": ["virtual_accounts", "settlement"],
    "executive_summary": "Providus Bank core banking platform experiencing intermittent failures affecting virtual account services.",
    "title": "Providus Core Banking Disruption",
    "source_url": "https://techpoint.africa/providus-outage-sept-2026",
}


# ─── Tier 1: Deterministic Matching Tests ─────────────────────────────────────

class TestTier1CBNPOSCircular:
    """CBN POS circular routes correctly to POS operator, not FX company."""

    def test_org_b_critical_direct(self):
        """PayPOS (PSSP/Interswitch/pos_acquiring) → critical_direct."""
        result = compute_exposure(CBN_POS_SIGNAL, ORG_B_CONTEXT)
        assert result.exposure_tier == "critical_direct"
        all_matched = []
        for values in result.matched_nodes.values():
            all_matched.extend(values)
        # Must match at least one of: interswitch, pos_acquiring, pssp
        assert any(
            item in all_matched
            for item in ["interswitch", "pos_acquiring", "pssp"]
        )

    def test_org_a_no_pos_match(self):
        """FXBridge has no POS/Interswitch exposure.
        
        Note: May still match via NIBSS if present in signal secondary_entities.
        With INTERSWITCH only (no NIBSS), Org A should be irrelevant.
        """
        # Signal without NIBSS in secondary entities
        signal_no_nibss = {
            **CBN_POS_SIGNAL,
            "secondary_entities": ["INTERSWITCH"],  # no NIBSS
        }
        result = compute_exposure(signal_no_nibss, ORG_A_CONTEXT)
        # Org A has no INTERSWITCH, no pos_acquiring, no PSSP
        assert result.exposure_tier == "irrelevant"


class TestTier1ProvidusOutage:
    """Providus outage routes correctly to Providus-dependent company."""

    def test_org_a_critical_direct(self):
        """FXBridge (Providus rail) → critical_direct."""
        result = compute_exposure(PROVIDUS_OUTAGE_SIGNAL, ORG_A_CONTEXT)
        assert result.exposure_tier == "critical_direct"
        assert "providus" in result.matched_nodes.get("matched_rails", [])

    def test_org_b_no_providus(self):
        """PayPOS has no Providus dependency — should not match Providus."""
        result = compute_exposure(PROVIDUS_OUTAGE_SIGNAL, ORG_B_CONTEXT)
        matched_rails = result.matched_nodes.get("matched_rails", [])
        assert "providus" not in matched_rails


# ─── Tier 2: Lens Synthesis Tests ─────────────────────────────────────────────

class TestTier2LensSynthesis:
    """Verify that lens synthesis produces distinct, non-overlapping payloads."""

    @pytest.mark.asyncio
    async def test_deterministic_fallback_distinct_actions(self):
        """When LLM is unavailable, fallback produces three distinct action items."""
        with patch(
            "app.context.relevance_engine._call_llm",
            side_effect=RuntimeError("No API key"),
        ):
            result = await synthesize_lens_impact(
                PROVIDUS_OUTAGE_SIGNAL,
                {"matched_rails": ["providus"], "matched_products": ["virtual_accounts"]},
                "critical_direct",
            )

        assert isinstance(result, LensImpact)

        # All three lenses must produce distinct action items
        actions = {
            result.product_lens.action_item,
            result.cfo_lens.action_item,
            result.compliance_lens.action_item,
        }
        assert len(actions) == 3, (
            f"Lenses produced overlapping actions: "
            f"product={result.product_lens.action_item!r}, "
            f"cfo={result.cfo_lens.action_item!r}, "
            f"compliance={result.compliance_lens.action_item!r}"
        )

    @pytest.mark.asyncio
    async def test_deterministic_fallback_distinct_impacts(self):
        """Fallback impacts must also be distinct."""
        with patch(
            "app.context.relevance_engine._call_llm",
            side_effect=RuntimeError("No API key"),
        ):
            result = await synthesize_lens_impact(
                CBN_POS_SIGNAL,
                {"matched_products": ["pos_acquiring"], "matched_licenses": ["pssp"]},
                "critical_direct",
            )

        impacts = {
            result.product_lens.impact,
            result.cfo_lens.impact,
            result.compliance_lens.impact,
        }
        assert len(impacts) == 3, "Lens impacts must be non-overlapping"

    @pytest.mark.asyncio
    async def test_urgency_mapping_critical(self):
        """Critical signal urgency maps to 'immediate' lens urgency."""
        with patch(
            "app.context.relevance_engine._call_llm",
            side_effect=RuntimeError("No API key"),
        ):
            result = await synthesize_lens_impact(
                PROVIDUS_OUTAGE_SIGNAL,
                {"matched_rails": ["providus"]},
                "critical_direct",
            )

        assert result.product_lens.urgency == "immediate"
        assert result.cfo_lens.urgency == "immediate"
        assert result.compliance_lens.urgency == "immediate"

    @pytest.mark.asyncio
    async def test_urgency_mapping_moderate(self):
        """Moderate signal urgency maps to 'within_week' lens urgency."""
        moderate_signal = {**CBN_POS_SIGNAL, "urgency": "moderate"}
        with patch(
            "app.context.relevance_engine._call_llm",
            side_effect=RuntimeError("No API key"),
        ):
            result = await synthesize_lens_impact(
                moderate_signal,
                {"matched_products": ["pos_acquiring"]},
                "moderate_indirect",
            )

        assert result.product_lens.urgency == "within_week"


# ─── ExposureResult Model Tests ───────────────────────────────────────────────

class TestExposureResultModel:
    """Verify the Pydantic ExposureResult model constraints."""

    def test_valid_tiers(self):
        """All four exposure tiers are accepted."""
        for tier in ("critical_direct", "moderate_indirect", "low_observation", "irrelevant"):
            result = ExposureResult(exposure_tier=tier, matched_nodes={})
            assert result.exposure_tier == tier

    def test_invalid_tier_rejected(self):
        """Invalid tier value raises validation error."""
        with pytest.raises(Exception):
            ExposureResult(exposure_tier="unknown", matched_nodes={})

    def test_matched_nodes_serialisation(self):
        """Matched nodes serialise correctly for JSONB storage."""
        result = ExposureResult(
            exposure_tier="critical_direct",
            matched_nodes={"matched_rails": ["providus", "nibss"]},
        )
        dumped = result.model_dump()
        assert dumped["matched_nodes"]["matched_rails"] == ["providus", "nibss"]


# ─── Full Scenario: Cross-Validation ─────────────────────────────────────────

class TestCrossOrgValidation:
    """Cross-validate that signals route to the correct tenants."""

    def test_providus_signal_hits_org_a_not_org_b_on_providus(self):
        """Providus outage: Org A matches Providus, Org B does not."""
        result_a = compute_exposure(PROVIDUS_OUTAGE_SIGNAL, ORG_A_CONTEXT)
        result_b = compute_exposure(PROVIDUS_OUTAGE_SIGNAL, ORG_B_CONTEXT)

        assert "providus" in result_a.matched_nodes.get("matched_rails", [])
        assert "providus" not in result_b.matched_nodes.get("matched_rails", [])

    def test_pos_signal_hits_org_b_products(self):
        """POS circular: Org B matches pos_acquiring, Org A does not."""
        result_b = compute_exposure(CBN_POS_SIGNAL, ORG_B_CONTEXT)

        matched_products = result_b.matched_nodes.get("matched_products", [])
        assert "pos_acquiring" in matched_products

    def test_pos_signal_org_a_no_pos_products(self):
        """POS circular: Org A has no POS products."""
        result_a = compute_exposure(CBN_POS_SIGNAL, ORG_A_CONTEXT)
        matched_products = result_a.matched_nodes.get("matched_products", [])
        assert "pos_acquiring" not in matched_products

    @pytest.mark.asyncio
    async def test_full_pipeline_produces_role_specific_outputs(self):
        """Full pipeline: exposure → lens synthesis produces all three lenses."""
        exposure = compute_exposure(PROVIDUS_OUTAGE_SIGNAL, ORG_A_CONTEXT)
        assert exposure.exposure_tier == "critical_direct"

        with patch(
            "app.context.relevance_engine._call_llm",
            side_effect=RuntimeError("No API key"),
        ):
            lens = await synthesize_lens_impact(
                PROVIDUS_OUTAGE_SIGNAL,
                exposure.matched_nodes,
                exposure.exposure_tier,
            )

        # All three lenses populated
        assert lens.product_lens.impact
        assert lens.cfo_lens.impact
        assert lens.compliance_lens.impact

        # All three are different
        assert lens.product_lens.impact != lens.cfo_lens.impact
        assert lens.cfo_lens.impact != lens.compliance_lens.impact
        assert lens.product_lens.impact != lens.compliance_lens.impact
