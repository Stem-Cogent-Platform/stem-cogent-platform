# MVP product correction - Track 2: Evidence Normalization & Confidence

Status: Verified locally; pending staging deployment.

## Overview

External fintech events often reach the ingestion pipeline through syndicated feeds, aggregator retweets, republications, and wire services. Previously, counting raw citation signals gave users an inflated sense of corroboration, and Dossier confidence bands could contradict Cogent CIL confidence ratings for the same underlying signal or brief.

Track 2 resolves this by:
1. Canonical URL normalization (query param stripping, tracking parameter removal, scheme/host canonicalization).
2. Content fingerprinting and publisher identity extraction.
3. Collapsing duplicate/syndicated evidence into single items with `duplicate_count` and earliest publication date.
4. Distinguishing primary authoritative sources (regulators, official payment network status/announcements) from secondary commentary.
5. Computing honest source metrics (`source_count`, `independent_source_count`, `primary_source_count`, `corroboration_strength`).
6. Unifying confidence mapping across Dossier and Cogent investigations via `map_confidence_to_cil` to eliminate contradictions.

## Corroboration Strengths

- `PRIMARY_CONFIRMED`: At least one verified primary source (tier 1 or authoritative regulatory/financial domain).
- `HIGHLY_CORROBORATED`: >= 3 independent sources.
- `CORROBORATED`: 2 independent sources.
- `SINGLE_SOURCE`: Exactly 1 independent source.
- `UNVERIFIED`: 0 sources or unconfirmed claims.

## Verification

- **Targeted Unit Tests**: 11/11 passed in `backend/tests/unit/test_evidence_normalization.py`:
  - URL normalization (stripping tracking parameters, canonicalizing scheme/host/port/trailing slash)
  - Primary source detection (tier 1 authorities, CBN, Paystack status, SEC Nigeria)
  - Publisher identity extraction (domain, source_id, source_name)
  - Source metrics calculation across primary, multiple independent, and syndications
  - Canonical evidence deduplication key generation
  - Duplicate evidence collapse (retaining earliest timestamp, counting duplicates)
  - Cross-surface confidence mapping (`HIGH_CONFIDENCE` -> `HIGH`, `LOW_CONFIDENCE` -> `LOW`, etc.)
  - Signal retrieval shared confidence consistency
  - Brief retrieval shared confidence consistency
  - Entity retrieval independent source metrics & confidence
  - Product API `/signals/{signal_id}` evidence normalization and source metrics integration
- **Regression Suite**: All 14 Track 1 relevance unit tests in `backend/tests/unit/test_product_correction_relevance.py` passed (25/25 combined).
- **Linter & Code Standards**: `ruff check` passed cleanly with zero warnings or errors.
- **Frontend Typecheck**: `npm run type-check` passed with zero errors (`tsc --noEmit`).
- **Frontend Unit Tests**: All 33 Vitest tests passed (`npm run test:unit`).

## Shared Confidence Consistency

| Dossier Confidence Band | Cogent CIL Confidence Indicator | Rationale |
|-------------------------|--------------------------------|-----------|
| `HIGH_CONFIDENCE`       | `HIGH`                         | Directly mapped |
| `MODERATE_CONFIDENCE`   | `MODERATE`                     | Directly mapped |
| `LOW_CONFIDENCE`        | `LOW`                          | Directly mapped; eliminates false "HIGH" in Cogent |
| `UNVERIFIED` / None     | `INSUFFICIENT_DATA`            | Directly mapped |
| Entity retrieval        | Derived from `corroboration_strength` | `PRIMARY_CONFIRMED` / `HIGHLY_CORROBORATED` -> `HIGH`, `CORROBORATED` -> `MODERATE`, `SINGLE_SOURCE` -> `LOW` |
