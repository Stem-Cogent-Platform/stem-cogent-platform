"""Evidence normalization, canonical source identity, and shared confidence basis.

Per Track 2 of MVP Product Correction Specification (Section 20):
- Normalize evidence by canonical source identity.
- Collapse repeated copies of the same article into a single evidence item.
- Track source_count, independent_source_count, primary_source_count, and corroboration_strength.
- Prevent Dossier and Cogent confidence contradiction with a shared confidence basis.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlparse


PRIMARY_DOMAINS = frozenset({
    "cbn.gov.ng",
    "sec.gov.ng",
    "ndpc.gov.ng",
    "status.paystack.com",
    "status.flutterwave.com",
    "nibss-plc.com.ng",
    "ngxgroup.com",
    "firs.gov.ng",
    "naicom.gov.ng",
    "pencom.gov.ng",
})

TRACKING_QUERY_PARAMS = frozenset({
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "_hsenc",
    "_hsmi",
    "ref",
    "source",
})


@dataclass(frozen=True, slots=True)
class SourceMetrics:
    source_count: int
    independent_source_count: int
    primary_source_count: int
    corroboration_strength: Literal[
        "PRIMARY_CONFIRMED",
        "HIGHLY_CORROBORATED",
        "CORROBORATED",
        "SINGLE_SOURCE",
        "UNVERIFIED",
    ]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_url(raw_url: str | None) -> str:
    """Normalize URL by stripping tracking parameters, default ports, and trailing slashes."""
    if not raw_url or not isinstance(raw_url, str):
        return ""
    parsed = urlparse(raw_url.strip())
    if not parsed.netloc:
        return raw_url.strip()

    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    # Remove standard ports
    if netloc.endswith(":80"):
        netloc = netloc[:-3]
    elif netloc.endswith(":443"):
        netloc = netloc[:-4]

    path = parsed.path.rstrip("/") if parsed.path != "/" else "/"

    filtered_query = [
        (k, v)
        for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_QUERY_PARAMS
    ]
    query_str = urlencode(filtered_query) if filtered_query else ""

    return f"{parsed.scheme.lower()}://{netloc}{path}{'?' + query_str if query_str else ''}"


def extract_publisher_identity(
    item: dict[str, Any],
) -> str:
    """Identify the distinct publisher/source behind an evidence item."""
    source_id = item.get("source_id")
    if source_id:
        return str(source_id)

    raw_url = item.get("canonical_url") or item.get("source_url")
    if raw_url:
        parsed = urlparse(str(raw_url).strip())
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain:
            return domain

    source_name = item.get("source_name")
    if source_name:
        return str(source_name).strip().lower()

    return str(item.get("id") or "unknown_source")


def is_primary_source(item: dict[str, Any]) -> bool:
    """Determine whether an evidence source is a primary/official authority."""
    tier = item.get("tier")
    if tier == 1:
        return True

    source_type = str(item.get("source_type") or "").upper()
    if source_type in {"PRIMARY", "REGULATORY", "INFRASTRUCTURE", "GOVERNMENT", "OFFICIAL"}:
        return True

    raw_url = item.get("canonical_url") or item.get("source_url")
    if raw_url:
        domain = urlparse(str(raw_url).strip()).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if domain in PRIMARY_DOMAINS:
            return True

    return False


def canonical_evidence_key(item: dict[str, Any]) -> str:
    """Generate a deterministic identity key for deduplicating repeated copies of an article."""
    canonical_url = normalize_url(item.get("canonical_url"))
    source_url = normalize_url(item.get("source_url"))
    url = canonical_url or source_url

    source_id = item.get("source_id")
    body_hash = item.get("body_text_hash")

    if source_id and body_hash:
        return f"body:{source_id}:{body_hash}"
    if url:
        return f"url:{url}"

    item_id = item.get("id")
    if item_id:
        return f"id:{item_id}"

    title = str(item.get("title") or "").strip().lower()
    source_name = str(item.get("source_name") or "").strip().lower()
    return f"title:{source_name}:{title}"


def compute_source_metrics(
    evidence_items: list[dict[str, Any]],
    raw_citation_count: int | None = None,
) -> SourceMetrics:
    """Compute standard source metrics across evidence items."""
    total_count = raw_citation_count if raw_citation_count is not None else len(evidence_items)

    unique_publishers: set[str] = set()
    primary_publishers: set[str] = set()

    for item in evidence_items:
        pub = extract_publisher_identity(item)
        unique_publishers.add(pub)
        if is_primary_source(item):
            primary_publishers.add(pub)

    independent_count = len(unique_publishers)
    primary_count = len(primary_publishers)

    CorroborationStrength = Literal[
        "PRIMARY_CONFIRMED",
        "HIGHLY_CORROBORATED",
        "CORROBORATED",
        "SINGLE_SOURCE",
        "UNVERIFIED",
    ]
    corroboration: CorroborationStrength
    if primary_count >= 1 and independent_count >= 2:
        corroboration = "PRIMARY_CONFIRMED"
    elif independent_count >= 3:
        corroboration = "HIGHLY_CORROBORATED"
    elif independent_count >= 2:
        corroboration = "CORROBORATED"
    elif independent_count == 1:
        corroboration = "SINGLE_SOURCE"
    else:
        corroboration = "UNVERIFIED"

    return SourceMetrics(
        source_count=max(total_count, independent_count),
        independent_source_count=independent_count,
        primary_source_count=primary_count,
        corroboration_strength=corroboration,
    )


def collapse_duplicate_evidence(
    evidence_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse duplicate evidence rows that describe the same story or URL."""
    collapsed: dict[str, dict[str, Any]] = {}

    for item in evidence_items:
        key = canonical_evidence_key(item)
        if key not in collapsed:
            entry = dict(item)
            entry["is_primary"] = is_primary_source(item)
            entry["duplicate_count"] = 1
            collapsed[key] = entry
        else:
            existing = collapsed[key]
            existing["duplicate_count"] = existing.get("duplicate_count", 1) + 1
            # Merge fields: keep earlier published_at if available
            existing_pub = existing.get("published_at")
            new_pub = item.get("published_at")
            if new_pub and (not existing_pub or new_pub < existing_pub):
                existing["published_at"] = new_pub
            if not existing.get("source_url") and item.get("source_url"):
                existing["source_url"] = item.get("source_url")
            if is_primary_source(item):
                existing["is_primary"] = True

    return list(collapsed.values())


def normalize_evidence_bundle(
    evidence_items: list[dict[str, Any]],
    raw_citation_count: int | None = None,
) -> tuple[list[dict[str, Any]], SourceMetrics]:
    """Normalize evidence items, collapse duplicate copies, and calculate metrics."""
    metrics = compute_source_metrics(evidence_items, raw_citation_count=raw_citation_count)
    deduped = collapse_duplicate_evidence(evidence_items)
    return deduped, metrics


def map_confidence_to_cil(
    confidence_band: str | None,
) -> Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT_DATA"]:
    """Align signal / brief confidence with Cogent CIL retrieval confidence.

    Prevents contradiction between Dossier confidence and Cogent answer confidence.
    """
    if not confidence_band:
        return "INSUFFICIENT_DATA"
    upper = str(confidence_band).upper()
    if "HIGH" in upper:
        return "HIGH"
    if "MODERATE" in upper or "MEDIUM" in upper:
        return "MODERATE"
    if "LOW" in upper:
        return "LOW"
    return "INSUFFICIENT_DATA"
