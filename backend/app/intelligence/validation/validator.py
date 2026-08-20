from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit


ValidationStatus = Literal["VALIDATED", "SUSPICIOUS", "REJECTED"]


@dataclass(frozen=True)
class SourceValidationProfile:
    source_type: str
    base_url: str | None
    region: str
    reliability_score: float
    schema_version: str


@dataclass(frozen=True)
class RawEvidenceInput:
    body: bytes
    payload_hash: str
    payload_size_bytes: int
    content_type: str
    source_url: str
    schema_version: str


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    source_trust_score: float
    authenticity_score: float
    manipulation_risk_score: float
    region_relevance_score: float
    flags: tuple[str, ...]


def validate_raw_evidence(
    profile: SourceValidationProfile,
    evidence: RawEvidenceInput,
) -> ValidationResult:
    flags: list[str] = []
    digest = f"sha256:{hashlib.sha256(evidence.body).hexdigest()}"
    if not evidence.body:
        flags.append("EMPTY_PAYLOAD")
    if digest != evidence.payload_hash:
        flags.append("PAYLOAD_HASH_MISMATCH")
    if len(evidence.body) != evidence.payload_size_bytes:
        flags.append("PAYLOAD_SIZE_MISMATCH")
    if evidence.schema_version != profile.schema_version:
        flags.append("SCHEMA_VERSION_MISMATCH")

    expected_signature = _signature_matches(profile.source_type, evidence.body)
    if not expected_signature:
        flags.append("CONTENT_SIGNATURE_MISMATCH")
    if not _source_matches(profile, evidence.source_url):
        flags.append("SOURCE_LOCATION_MISMATCH")
    if b"\x00" in evidence.body and profile.source_type not in {"PDF", "USER_UPLOAD"}:
        flags.append("UNEXPECTED_BINARY_CONTENT")
    lowered = evidence.body[:8192].lower()
    if profile.source_type == "HTML" and any(
        marker in lowered
        for marker in (b"access denied", b"404 not found", b"service unavailable")
    ):
        flags.append("HTML_ERROR_DOCUMENT")
    if profile.reliability_score < 0.60:
        flags.append("LOW_SOURCE_RELIABILITY")

    integrity_failure = any(
        flag in flags
        for flag in (
            "EMPTY_PAYLOAD",
            "PAYLOAD_HASH_MISMATCH",
            "PAYLOAD_SIZE_MISMATCH",
            "SCHEMA_VERSION_MISMATCH",
        )
    )
    authenticity_penalty = 0.0
    if "CONTENT_SIGNATURE_MISMATCH" in flags:
        authenticity_penalty += 0.35
    if "SOURCE_LOCATION_MISMATCH" in flags:
        authenticity_penalty += 0.35
    authenticity = round(max(0.0, 1.0 - authenticity_penalty), 3)
    manipulation_flags = {
        "CONTENT_SIGNATURE_MISMATCH",
        "SOURCE_LOCATION_MISMATCH",
        "UNEXPECTED_BINARY_CONTENT",
        "HTML_ERROR_DOCUMENT",
    }
    manipulation_risk = round(
        min(1.0, sum(flag in manipulation_flags for flag in flags) * 0.25), 3
    )
    region_score = 1.0 if profile.region == "NG" else 0.5
    if integrity_failure:
        status: ValidationStatus = "REJECTED"
    elif flags or authenticity < 0.70:
        status = "SUSPICIOUS"
    else:
        status = "VALIDATED"
    return ValidationResult(
        status=status,
        source_trust_score=round(max(0.0, min(1.0, profile.reliability_score)), 3),
        authenticity_score=authenticity,
        manipulation_risk_score=manipulation_risk,
        region_relevance_score=region_score,
        flags=tuple(sorted(flags)),
    )


def _source_matches(profile: SourceValidationProfile, source_url: str) -> bool:
    source = urlsplit(source_url)
    if profile.source_type == "USER_UPLOAD":
        return source.scheme == "s3" and source.path.startswith("/tenant/")
    if not profile.base_url:
        return False
    registered = urlsplit(profile.base_url)
    return (
        source.scheme == "https"
        and registered.scheme == "https"
        and source.hostname == registered.hostname
    )


def _signature_matches(source_type: str, body: bytes) -> bool:
    stripped = body.lstrip()
    if source_type == "RSS":
        return stripped.startswith((b"<?xml", b"<rss", b"<feed"))
    if source_type in {"API", "LIVE_SEARCH"}:
        try:
            json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return False
        return True
    if source_type == "HTML":
        lowered = stripped[:256].lower()
        return lowered.startswith((b"<!doctype html", b"<html"))
    if source_type == "PDF":
        return body.startswith(b"%PDF-")
    if source_type == "USER_UPLOAD":
        return bool(body)
    return False
