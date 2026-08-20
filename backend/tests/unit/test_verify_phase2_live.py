from app.ops.verify_phase2_live import failed_strict_checks


def test_strict_phase_two_evidence_passes_complete_live_search_path() -> None:
    evidence = {
        "active_sources": 17,
        "source_types": {"RSS": 4, "LIVE_SEARCH": 1},
        "taxonomy_domains": 8,
        "taxonomy_subcategories": 42,
        "job_statuses": {"COMPLETED": 17},
        "raw_statuses": {"VALIDATED": 16},
        "normalized_signals": 40,
        "live_search_jobs": 2,
        "live_search_raw": 2,
        "live_search_signals": 20,
    }

    assert failed_strict_checks(evidence) == []


def test_strict_phase_two_evidence_reports_each_missing_live_search_stage() -> None:
    failures = failed_strict_checks(
        {
            "active_sources": 17,
            "source_types": {"RSS": 4, "LIVE_SEARCH": 1},
            "taxonomy_domains": 8,
            "taxonomy_subcategories": 42,
            "job_statuses": {"COMPLETED": 16},
            "raw_statuses": {"VALIDATED": 15},
            "normalized_signals": 38,
            "live_search_jobs": 1,
            "live_search_raw": 0,
            "live_search_signals": 0,
        }
    )

    assert failures == [
        "live-search evidence archived",
        "live-search signal normalized",
    ]
