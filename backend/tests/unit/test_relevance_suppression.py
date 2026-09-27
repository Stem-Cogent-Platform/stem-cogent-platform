"""Unit tests for the relevance feedback learning loop and suppression down-ranking."""

from __future__ import annotations

from app.context.relevance_engine import compute_exposure


def _sample_tenant_profile() -> dict:
    return {
        "operating_licenses": ["PSSP", "SWITCHING"],
        "active_products": ["pos_acquiring", "virtual_accounts", "crypto_custody"],
        "clearing_rails": ["NIBSS", "PROVIDUS"],
        "relevance_suppression_tags": [],
    }


def _crypto_signal() -> dict:
    return {
        "signal_type": "regulatory_mandate",
        "urgency": "high",
        "primary_entity": "Binance Nigeria",
        "secondary_entities": ["SEC", "CryptoExchange"],
        "affected_sectors": ["crypto_custody"],
        "executive_summary": "SEC updates rules on digital assets and virtual asset providers.",
    }


def _switching_signal() -> dict:
    return {
        "signal_type": "rail_degradation",
        "urgency": "critical",
        "primary_entity": "NIBSS",
        "secondary_entities": [],
        "affected_sectors": ["switching", "settlement"],
        "executive_summary": "NIBSS NIP experiencing intermittent latency.",
    }


def test_baseline_without_suppression():
    profile = _sample_tenant_profile()
    signal = _crypto_signal()
    # High urgency + active product crypto_custody -> critical_direct
    result = compute_exposure(signal, profile)
    assert result.exposure_tier == "critical_direct"
    assert "crypto_custody" in result.matched_nodes.get("matched_products", [])


def test_suppression_down_ranks_tier():
    profile = _sample_tenant_profile()
    # User previously dismissed crypto signals, tagging crypto_custody with penalty weight 0.5
    profile["relevance_suppression_tags"] = [
        {"tag": "crypto_custody", "penalty_weight": 0.5, "dismissed_count": 2},
    ]
    signal = _crypto_signal()
    result = compute_exposure(signal, profile)
    # Down-ranked from critical_direct to moderate_indirect
    assert result.exposure_tier == "moderate_indirect"
    assert "crypto_custody" in result.matched_nodes.get("suppressed_tags", [])


def test_high_suppression_renders_signal_irrelevant():
    profile = _sample_tenant_profile()
    # User strongly dismissed Binance & crypto multiple times
    profile["relevance_suppression_tags"] = [
        {"tag": "Binance Nigeria", "penalty_weight": 0.75, "dismissed_count": 3},
        {"tag": "crypto_custody", "penalty_weight": 0.5, "dismissed_count": 2},
    ]
    signal = _crypto_signal()
    result = compute_exposure(signal, profile)
    # Cumulative penalty >= 1.0 -> down-ranked all the way to irrelevant
    assert result.exposure_tier == "irrelevant"
    assert "suppressed_tags" in result.matched_nodes


def test_unrelated_signal_unaffected_by_suppression():
    profile = _sample_tenant_profile()
    profile["relevance_suppression_tags"] = [
        {"tag": "crypto_custody", "penalty_weight": 1.0},
    ]
    # NIBSS signal has no crypto tags
    signal = _switching_signal()
    result = compute_exposure(signal, profile)
    assert result.exposure_tier == "critical_direct"
    assert "suppressed_tags" not in result.matched_nodes
