# MVP product correction - Track 5: Internal-First Retrieval & Evidence Sufficiency

Status: Verified locally; ready for staging deployment.

## Overview

In the Stem Cogent decision intelligence architecture, Cogent must never invoke external search providers prematurely or send private company context outwards. Before live search (Track 6), Cogent must exhaust internal intelligence and render an explicit, auditable evidence-sufficiency decision.

Track 5 implements:

1. **Internal-First Retrieval Expansion (`backend/app/cil/retrieval.py`)**:
   - Queries focal intelligence object (Signal, Signal Dossier, Decision Brief, or Entity).
   - Enriches context with company context (profile, business model, active company objects: competitors, dependencies, regulators).
   - Enriches context with user context (Decision Lens role, responsibilities, and active focus areas from `context.user_focus_areas`).
   - Retrieves related intelligence: signals in the same primary domain or referencing common company counterparties.
   - Normalizes stored evidence: deduplicated citations, primary source backing, and corroboration metrics.
   - Attaches an explicit `SufficiencyDecision` to `structured_context["sufficiency"]`.

2. **Evidence Sufficiency Decision Engine (`backend/app/cil/sufficiency.py`)**:
   - `SufficiencyStatus`: Enum (`SUFFICIENT`, `INSUFFICIENT_INTERNAL`, `NEEDS_LIVE_SEARCH`, `STALE`).
   - `EvidenceGapType`: Enum (`NONE`, `NO_MATCHED_RECORDS`, `UNINDEXED_ENTITY`, `EXPLICIT_EXTERNAL_REQUEST`, `LOW_CORROBORATION`, `STALE_RECORD`).
   - `SufficiencyDecision`: Pydantic model with `status`, `gap_type`, `reason`, `recommended_action`, `missing_elements`, `independent_source_count`, and `corroboration_strength`.
   - `evaluate_evidence_sufficiency(query, retrieval, intent, thread_messages_count)`:
     - Detects explicit requests for real-time / web news (`NEEDS_LIVE_SEARCH`, `EXPLICIT_EXTERNAL_REQUEST`).
     - Detects ungrounded anchors with 0 citations or insufficient data (`INSUFFICIENT_INTERNAL`, `NO_MATCHED_RECORDS`).
     - Detects stale incident records lacking resolution confirmation (`STALE`, `STALE_RECORD`).
     - Detects uncorroborated single-source claims for critical decision queries (`INSUFFICIENT_INTERNAL`, `LOW_CORROBORATION`).
     - Confirms sufficient internal evidence when backed by multi-source verified signals (`SUFFICIENT`, `NONE`).

3. **Cognitive Synthesis Boundary (`backend/app/cil/answering.py`)**:
   - In `deterministic_answer`, evaluates the sufficiency decision:
     - When `SUFFICIENT`: Generates full grounded executive analysis tailored to role and intent.
     - When `NEEDS_LIVE_SEARCH`: Transparently declares the need for live research, details the exact missing elements, and recommends targeted external search without hallucinating.
     - When `INSUFFICIENT_INTERNAL`: Transparently states the evidence limitation and advises a MONITOR posture.

4. **API Integration (`backend/app/api/v1/cil.py`)**:
   - Passes user `query` to `retrieve_context`.
   - Adds `evidence_sufficiency` field to `CILQueryResponse`.
   - Records `sufficiency` status in `feedback.product_events` and `billing.usage_events` analytics.

## Verification

- **Targeted Evidence Sufficiency Suite**: 6/6 passed in `backend/tests/unit/test_evidence_sufficiency.py`:
  - `test_evaluate_evidence_sufficiency_sufficient` (Multi-source verified context)
  - `test_evaluate_evidence_sufficiency_explicit_live_search_request` (Real-time and web query detection)
  - `test_evaluate_evidence_sufficiency_insufficient_data` (Ungrounded 0-citation anchors)
  - `test_evaluate_evidence_sufficiency_stale_record` (Stale incident detection)
  - `test_deterministic_answer_with_needs_live_search` (Transparent gap declaration)
  - `test_deterministic_answer_with_insufficient_internal` (Monitor posture guidance)
- **Combined Regression Suite**: 53/53 passed:
  - Track 1 relevance: 14 passed
  - Track 2 evidence normalization: 11 passed
  - Track 3 intent router: 7 passed
  - Track 4 investigation threads: 4 passed
  - Track 5 evidence sufficiency: 6 passed
  - Phase 3 API tests: 11 passed
- **Code Standards & Linter**: `ruff check` passed cleanly (0 errors) across `backend/app/cil` and `backend/app/api/v1/cil.py`.
- **Frontend Typecheck**: `npm run type-check` passed with 0 errors (`tsc --noEmit`).
- **Frontend Unit Tests**: All 33 Vitest tests passed (`npm run test:unit`).

## Next Steps

With Track 5 verified, the implementation sequence advances to **Track 6 — Live search integration** (SerpApi / approved provider integration with server-side secrets, privacy boundary, and rate limits).
