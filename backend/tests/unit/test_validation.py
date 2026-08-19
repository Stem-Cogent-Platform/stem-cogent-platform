import hashlib

from app.intelligence.validation import (
    RawEvidenceInput,
    SourceValidationProfile,
    validate_raw_evidence,
)


def _evidence(body: bytes, **overrides) -> RawEvidenceInput:
    values = {
        "body": body,
        "payload_hash": f"sha256:{hashlib.sha256(body).hexdigest()}",
        "payload_size_bytes": len(body),
        "content_type": "application/json",
        "source_url": "https://status.nibss-plc.com.ng/incidents/1.json",
        "schema_version": "1.0",
    }
    values.update(overrides)
    return RawEvidenceInput(**values)


PROFILE = SourceValidationProfile(
    source_type="API",
    base_url="https://status.nibss-plc.com.ng/incidents",
    region="NG",
    reliability_score=0.95,
    schema_version="1.0",
)


def test_authoritative_intact_payload_is_validated() -> None:
    result = validate_raw_evidence(PROFILE, _evidence(b'{"status":"degraded"}'))

    assert result.status == "VALIDATED"
    assert result.flags == ()
    assert result.source_trust_score == 0.95
    assert result.authenticity_score == 1.0


def test_suspicious_payload_routes_for_review() -> None:
    result = validate_raw_evidence(
        PROFILE,
        _evidence(
            b"<html>404 Not Found</html>",
            source_url="https://unregistered.example/status",
        ),
    )

    assert result.status == "SUSPICIOUS"
    assert "CONTENT_SIGNATURE_MISMATCH" in result.flags
    assert "SOURCE_LOCATION_MISMATCH" in result.flags
    assert result.manipulation_risk_score > 0


def test_archive_integrity_failure_is_rejected_without_progression() -> None:
    result = validate_raw_evidence(
        PROFILE,
        _evidence(b'{"status":"ok"}', payload_hash="sha256:not-the-archive-hash"),
    )

    assert result.status == "REJECTED"
    assert result.flags == ("PAYLOAD_HASH_MISMATCH",)


def test_low_reliability_source_is_suspicious_even_with_valid_content() -> None:
    profile = SourceValidationProfile(
        source_type="API",
        base_url=PROFILE.base_url,
        region="NG",
        reliability_score=0.40,
        schema_version="1.0",
    )

    result = validate_raw_evidence(profile, _evidence(b'{"status":"ok"}'))

    assert result.status == "SUSPICIOUS"
    assert result.flags == ("LOW_SOURCE_RELIABILITY",)
