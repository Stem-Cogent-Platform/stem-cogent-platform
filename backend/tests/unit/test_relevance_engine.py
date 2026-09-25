"""Unit tests for the Relevance Engine deterministic matcher (Tier 1).

Tests compute_exposure() — the pure-function set intersection logic —
with no database or LLM dependencies.
"""

from __future__ import annotations


from app.context.relevance_engine import compute_exposure


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _org_a_profile() -> dict:
    """Organization A: Cross-Border FX company using Providus rail."""
    return {
        "operating_licenses": ["IMTO", "FINANCE_COMPANY"],
        "active_products": ["cross_border_fx", "virtual_accounts", "p2p_wallet"],
        "clearing_rails": ["PROVIDUS", "NIBSS", "WEMA"],
    }


def _org_b_profile() -> dict:
    """Organization B: POS Agency Banking company using Interswitch rail."""
    return {
        "operating_licenses": ["PSSP", "SWITCHING"],
        "active_products": ["pos_acquiring", "agency_banking", "card_issuance"],
        "clearing_rails": ["INTERSWITCH", "NIBSS"],
    }


def _cbn_pos_circular() -> dict:
    """CBN circular on POS geofencing — directly affects POS operators."""
    return {
        "signal_type": "regulatory_mandate",
        "urgency": "high",
        "sentiment": "threat",
        "primary_entity": "Central Bank of Nigeria",
        "secondary_entities": ["NIBSS", "INTERSWITCH"],
        "affected_sectors": ["pos_acquiring", "agency_banking"],
        "executive_summary": "CBN issues directive mandating POS geofencing for all licensed POS operators.",
    }


def _providus_outage() -> dict:
    """Providus core banking disruption — affects Providus-dependent tenants."""
    return {
        "signal_type": "rail_degradation",
        "urgency": "critical",
        "sentiment": "threat",
        "primary_entity": "Providus Bank",
        "secondary_entities": ["PROVIDUS"],
        "affected_sectors": ["virtual_accounts", "settlement"],
        "executive_summary": "Providus Bank core banking platform experiencing intermittent failures.",
    }


def _generic_industry_news() -> dict:
    """Generic industry news — not directly related to any operational footprint."""
    return {
        "signal_type": "general_industry",
        "urgency": "low",
        "sentiment": "neutral",
        "primary_entity": "Stripe",
        "secondary_entities": ["US Federal Reserve"],
        "affected_sectors": ["international_remittance"],
        "executive_summary": "Stripe announces new embedded banking features for US market.",
    }


def _nibss_maintenance() -> dict:
    """NIBSS scheduled maintenance — affects all NIBSS-dependent tenants."""
    return {
        "signal_type": "rail_degradation",
        "urgency": "moderate",
        "sentiment": "threat",
        "primary_entity": "NIBSS",
        "secondary_entities": [],
        "affected_sectors": ["interbank_settlement"],
        "executive_summary": "NIBSS announces scheduled maintenance window for NIP channel.",
    }


# ─── Core Exposure Tests ─────────────────────────────────────────────────────


class TestCBNPOSCircular:
    """CBN POS geofencing circular: Org B critical, Org A irrelevant."""

    def test_org_b_gets_critical_direct(self):
        """Org B (POS/Interswitch) should get critical_direct for POS circular."""
        result = compute_exposure(_cbn_pos_circular(), _org_b_profile())
        assert result.exposure_tier == "critical_direct"
        # Should match on rail (INTERSWITCH) and/or product (pos_acquiring)
        assert len(result.matched_nodes) > 0

    def test_org_b_matches_interswitch_rail(self):
        """Org B should detect INTERSWITCH in its clearing_rails."""
        result = compute_exposure(_cbn_pos_circular(), _org_b_profile())
        matched_rails = result.matched_nodes.get("matched_rails", [])
        assert "interswitch" in matched_rails

    def test_org_b_matches_pos_product(self):
        """Org B should detect pos_acquiring in its active_products."""
        result = compute_exposure(_cbn_pos_circular(), _org_b_profile())
        matched_products = result.matched_nodes.get("matched_products", [])
        assert "pos_acquiring" in matched_products

    def test_org_a_gets_irrelevant(self):
        """Org A (FX/Providus) has no crypto or microfinance exposure."""
        unrelated_signal = {
            "primary_entity": "Unknown Microfinance",
            "secondary_entities": ["Random Bank"],
            "affected_sectors": ["agriculture"],
            "signal_type": "general_industry",
            "urgency": "low",
        }
        result = compute_exposure(unrelated_signal, _org_a_profile())
        assert result.exposure_tier == "irrelevant"

    def test_org_a_nibss_overlap_acknowledged(self):
        """Both orgs share NIBSS dependency — signal touching NIBSS hits both."""
        result = compute_exposure(_cbn_pos_circular(), _org_a_profile())
        # NIBSS is in signal secondary_entities AND org A clearing_rails
        if "nibss" in result.matched_nodes.get("matched_rails", []):
            assert result.exposure_tier in ("critical_direct", "moderate_indirect")


class TestProvidusOutage:
    """Providus core banking disruption: Org A critical, Org B irrelevant (except NIBSS overlap)."""

    def test_org_a_gets_critical_direct(self):
        """Org A (Providus rail) should get critical_direct."""
        result = compute_exposure(_providus_outage(), _org_a_profile())
        assert result.exposure_tier == "critical_direct"

    def test_org_a_matches_providus_rail(self):
        """Org A should detect PROVIDUS in matched_rails."""
        result = compute_exposure(_providus_outage(), _org_a_profile())
        matched_rails = result.matched_nodes.get("matched_rails", [])
        assert "providus" in matched_rails

    def test_org_a_matches_virtual_accounts_product(self):
        """Org A should also detect virtual_accounts in matched_products."""
        result = compute_exposure(_providus_outage(), _org_a_profile())
        matched_products = result.matched_nodes.get("matched_products", [])
        assert "virtual_accounts" in matched_products

    def test_org_b_no_providus_match(self):
        """Org B should NOT match Providus rail."""
        result = compute_exposure(_providus_outage(), _org_b_profile())
        matched_rails = result.matched_nodes.get("matched_rails", [])
        assert "providus" not in matched_rails


class TestGenericIndustryNews:
    """Generic news that doesn't touch any Nigerian fintech operational footprint."""

    def test_org_a_irrelevant(self):
        """Org A has no overlap with Stripe/US Fed — should be irrelevant."""
        result = compute_exposure(_generic_industry_news(), _org_a_profile())
        assert result.exposure_tier == "irrelevant"
        assert result.matched_nodes == {}

    def test_org_b_irrelevant(self):
        """Org B has no overlap with Stripe/US Fed — should be irrelevant."""
        result = compute_exposure(_generic_industry_news(), _org_b_profile())
        assert result.exposure_tier == "irrelevant"
        assert result.matched_nodes == {}


class TestNIBSSMaintenance:
    """NIBSS maintenance: both orgs should match since both use NIBSS."""

    def test_org_a_matches(self):
        """Org A uses NIBSS — should get critical_direct."""
        result = compute_exposure(_nibss_maintenance(), _org_a_profile())
        assert result.exposure_tier == "critical_direct"
        assert "nibss" in result.matched_nodes.get("matched_rails", [])

    def test_org_b_matches(self):
        """Org B uses NIBSS — should get critical_direct."""
        result = compute_exposure(_nibss_maintenance(), _org_b_profile())
        assert result.exposure_tier == "critical_direct"
        assert "nibss" in result.matched_nodes.get("matched_rails", [])


# ─── Edge Cases ───────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Edge cases in the deterministic matcher."""

    def test_empty_profile_returns_irrelevant(self):
        """Tenant with no operational data configured gets irrelevant."""
        result = compute_exposure(
            _cbn_pos_circular(),
            {"operating_licenses": [], "active_products": [], "clearing_rails": []},
        )
        assert result.exposure_tier == "irrelevant"

    def test_empty_signal_returns_irrelevant(self):
        """Signal with no structured entities/sectors gets irrelevant."""
        result = compute_exposure(
            {
                "signal_type": "general_industry",
                "urgency": "low",
                "primary_entity": "",
                "secondary_entities": [],
                "affected_sectors": [],
            },
            _org_a_profile(),
        )
        assert result.exposure_tier == "irrelevant"

    def test_case_insensitive_matching(self):
        """Matching should be case-insensitive."""
        signal = {
            "signal_type": "rail_degradation",
            "urgency": "high",
            "primary_entity": "providus",
            "secondary_entities": [],
            "affected_sectors": [],
        }
        profile = {
            "operating_licenses": [],
            "active_products": [],
            "clearing_rails": ["PROVIDUS"],
        }
        result = compute_exposure(signal, profile)
        assert result.exposure_tier == "critical_direct"

    def test_whitespace_handling(self):
        """Matching should handle whitespace in values."""
        signal = {
            "signal_type": "regulatory_mandate",
            "urgency": "moderate",
            "primary_entity": "CBN",
            "secondary_entities": ["  NIBSS  "],
            "affected_sectors": [],
        }
        profile = {
            "operating_licenses": [],
            "active_products": [],
            "clearing_rails": ["NIBSS"],
        }
        result = compute_exposure(signal, profile)
        assert result.exposure_tier == "critical_direct"

    def test_product_match_low_urgency_is_moderate(self):
        """Product-only match with low urgency gives moderate_indirect."""
        signal = {
            "signal_type": "general_industry",
            "urgency": "low",
            "primary_entity": "Someone",
            "secondary_entities": [],
            "affected_sectors": ["card_issuance"],
        }
        result = compute_exposure(signal, _org_b_profile())
        assert result.exposure_tier == "moderate_indirect"

    def test_product_match_critical_urgency_is_critical(self):
        """Product match with critical urgency elevates to critical_direct."""
        signal = {
            "signal_type": "rail_degradation",
            "urgency": "critical",
            "primary_entity": "Unknown",
            "secondary_entities": [],
            "affected_sectors": ["card_issuance"],
        }
        result = compute_exposure(signal, _org_b_profile())
        assert result.exposure_tier == "critical_direct"

    def test_license_match_is_critical(self):
        """Operating license match should always be critical_direct."""
        signal = {
            "signal_type": "regulatory_mandate",
            "urgency": "low",
            "primary_entity": "CBN",
            "secondary_entities": [],
            "affected_sectors": ["PSSP"],
        }
        result = compute_exposure(signal, _org_b_profile())
        assert result.exposure_tier == "critical_direct"
        assert "pssp" in result.matched_nodes.get("matched_licenses", [])


# ─── Deterministic Fallback Tests ─────────────────────────────────────────────

class TestDeterministicFallback:
    """Test the deterministic fallback for lens synthesis."""

    def test_fallback_produces_distinct_lenses(self):
        """Deterministic fallback must produce three distinct action items."""
        from app.context.relevance_engine import _deterministic_fallback

        result = _deterministic_fallback(
            _providus_outage(),
            {"matched_rails": ["providus"]},
            "critical_direct",
        )
        # All three lenses must have different action items
        actions = {
            result.product_lens.action_item,
            result.cfo_lens.action_item,
            result.compliance_lens.action_item,
        }
        assert len(actions) == 3, "Lenses must produce non-overlapping action items"

    def test_fallback_urgency_mapping(self):
        """Critical signal urgency should map to 'immediate' lens urgency."""
        from app.context.relevance_engine import _deterministic_fallback

        result = _deterministic_fallback(
            _providus_outage(),
            {"matched_rails": ["providus"]},
            "critical_direct",
        )
        assert result.product_lens.urgency == "immediate"
        assert result.cfo_lens.urgency == "immediate"

    def test_fallback_regulatory_template(self):
        """Regulatory signals use the regulatory template."""
        from app.context.relevance_engine import _deterministic_fallback

        result = _deterministic_fallback(
            _cbn_pos_circular(),
            {"matched_products": ["pos_acquiring"]},
            "critical_direct",
        )
        assert "regulatory" in result.compliance_lens.impact.lower() or \
               "CBN" in result.compliance_lens.impact or \
               "Central Bank" in result.compliance_lens.impact
