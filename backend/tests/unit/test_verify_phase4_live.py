from app.ops.verify_phase4_live import failed_checks


def test_global_pipeline_checks_require_real_cited_output() -> None:
    evidence = {
        "raw_signals": 1,
        "validated_raw_signals": 1,
        "signals": 1,
        "cited_global_outputs": 0,
    }

    assert failed_checks(evidence, require_tenant_delivery=False) == [
        "cited Global Output completed"
    ]


def test_tenant_delivery_checks_cover_every_persisted_surface() -> None:
    evidence = {
        "raw_signals": 1,
        "validated_raw_signals": 1,
        "signals": 1,
        "cited_global_outputs": 1,
        "assessments": 1,
        "company_briefs": 1,
        "personal_briefs": 1,
        "alerts": 1,
        "digests": 0,
    }

    assert failed_checks(evidence, require_tenant_delivery=True) == [
        "digest containing the brief persisted"
    ]
