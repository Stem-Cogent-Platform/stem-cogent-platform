# MVP Product Correction — Track 6: Live Search Integration

Status: Verified locally; ready for staging deployment.

## Overview

Per Track 6 of the MVP Product Correction Specification (`docs/stem-cogent-mvp-product-correction-spec.md`, Sections 16, 17, 18), live search connects Stem Cogent to external discovery providers (SerpApi) strictly as server-side pull intelligence when internal-first retrieval (Track 5) declares `NEEDS_LIVE_SEARCH` or when the user initiates an open research inquiry.

Track 6 implements:

1. **Server-Side Production Configuration (`backend/app/core/config.py`)**:
   - `SERPAPI_API_KEY_ARN` (resolved via AWS Secrets Manager with `get_scalar_secret`)
   - `SERPAPI_API_KEY` (direct environment fallback for staging/local development)
   - `SERPAPI_BASE_URL` (`https://serpapi.com/search.json`)
   - `SERPAPI_ENGINE` (`google`)
   - `LIVE_SEARCH_ENABLED` (`True`)
   - `LIVE_SEARCH_TIMEOUT_SECONDS` (`8.0`)
   - `LIVE_SEARCH_RATE_LIMIT_PER_MINUTE` (`10`)

2. **Strict Outbound Privacy Boundary (`backend/app/intelligence/live_search/privacy.py`)**:
   - Strips confidential company name, internal tenant IDs, UUIDs, email addresses, and account numbers.
   - Strips conversational and internal role framing (`"how does this affect our margin as CFO"`).
   - Extracts and preserves public entity names (`"Moniepoint"`, `"CBN"`, `"NIBSS"`, `"Flutterwave"`) and market concepts (`"agency fee increase"`).
   - Anchors search to the Nigerian fintech jurisdiction (`"Nigeria"`).
   - Ensures no private Company Context or internal metrics ever leave the Stem infrastructure.

3. **Per-Tenant Rate Limiter (`backend/app/intelligence/live_search/rate_limiter.py`)**:
   - Implements Redis rate-limiting using `live_search:rate:{tenant_id}` with 60-second window expiration.
   - Provides resilient in-memory sliding window fallback when Redis is unconfigured or offline.
   - Prevents quota exhaustion and unexpected upstream cost overruns.

4. **Result Date/Source Normalization & Deduplication (`backend/app/intelligence/live_search/normalizer.py`)**:
   - Normalizes URLs (strips `utm_*`, `fbclid`, tracking parameters, default ports, trailing slashes).
   - Converts relative timestamps (`"2 hours ago"`, `"1 day ago"`) and date strings into ISO 8601 strings.
   - Generates consistent canonical identity hashes (`SHA256` digest).
   - Deduplicates identical results and suppresses any external URLs already present in internal citations.

5. **Async Provider Client & Graceful Degradation (`backend/app/intelligence/live_search/client.py`, `service.py`)**:
   - Implements non-blocking `SerpApiClient` using `httpx.AsyncClient` with strict 8.0-second timeout.
   - Safely catches `LiveSearchTimeoutError`, `LiveSearchRateLimitError` (HTTP 429), and `LiveSearchProviderError` (HTTP 5xx).
   - Degrades gracefully: returns structured execution status without raising unhandled 500 exceptions or blocking executive queries.

6. **Cogent CIL Synthesis & Citations (`backend/app/cil/answering.py`, `backend/app/api/v1/cil.py`)**:
   - Synthesizes retrieved external live search reports into an executive answer combining verified internal foundation with external market findings.
   - Formats external citations in `CILQueryResponse.citations`.
   - In the event of rate-limiting or provider timeout, transparently reports the limitation and advises an interim `MONITOR` decision posture.

## Verification

- **Targeted Live Search Test Suite (`backend/tests/unit/test_live_search.py`)**: 7/7 passed:
  - `test_privacy_boundary_sanitizes_confidential_terms_and_preserves_public_entities` (Confidential context & UUID stripping)
  - `test_normalization_and_deduplication` (Canonical URL normalization, duplicate collapse, internal exclusion)
  - `test_date_parser_relative_and_absolute` (Relative time parsing)
  - `test_rate_limiter_in_memory_quota` (Per-tenant quota enforcement)
  - `test_live_search_service_success` (End-to-end execution with SerpApi mocking)
  - `test_live_search_graceful_degradation` (Timeout and 429 quota handling)
  - `test_deterministic_answering_synthesizes_live_search_evidence` (CIL synthesis & citation generation)

- **Combined Regression Test Suite across Tracks 2–6**: 24/24 passed:
  - `test_evidence_normalization.py` (Track 2)
  - `test_cogent_intent_router.py` (Track 3)
  - `test_investigation_threads.py` (Track 4)
  - `test_evidence_sufficiency.py` (Track 5)
  - `test_live_search.py` (Track 6)

- **Linter Verification**: `ruff check` passed with 0 errors across `backend/app/core/config.py`, `backend/app/cil`, `backend/app/intelligence/live_search`, and `backend/app/api/v1/cil.py`.
- **Frontend Typecheck**: `npm run type-check` passed with 0 errors (`tsc --noEmit`).
- **Frontend Unit Tests**: All 33 Vitest tests passed (`npm run test:unit`).
