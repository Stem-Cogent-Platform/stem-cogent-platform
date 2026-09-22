# MVP product correction - Track 3: Cogent Intent Router

Status: Verified locally; ready for staging deployment.

## Overview

Cogent is designed as a bounded intelligence investigation agent rather than a generic chatbot. Previously, Cogent returned the same concatenated summary fragments regardless of whether the user asked about what happened, company relevance, evidence verification, competitor comparison, downstream implications, actionable decisions, or unknown gaps.

Track 3 corrects this by implementing:
1. **Canonical 7-Intent Classification & Router**:
   - `EXPLAIN`: Fact-focused event description, background, and timeline.
   - `RELEVANCE`: Company-specific connection, matched dependencies/competitors/regulators, and Decision Lens role perspective.
   - `EVIDENCE`: Independent source counts, primary sources, corroboration rating, and citation evaluation.
   - `COMPARE`: Comparative analysis against competitors (e.g. Moniepoint, OPay, Flutterwave) and market peers.
   - `IMPLICATION`: Downstream financial, operational, and regulatory second-order fallout.
   - `DECISION`: Recommended decision posture (`NO_ACTION`, `MONITOR`, `INVESTIGATE`, `DECISION_REQUIRED`), action guidance, and validation checkpoints.
   - `RESEARCH`: Critical unknowns, unconfirmed claims, evidence limitations, and follow-up inquiries.
2. **Context Enrichment (4 Layers)**:
   - User context: Decision Lens role, responsibilities, and focus areas.
   - Company context: company profile, products, business model, and active company objects.
   - Current object: signal, brief, or entity.
   - Verified evidence: canonical citations and normalized source metrics.
3. **Role-Awareness**:
   - The same signal produces role-divergent interpretations for `RELEVANCE`:
     - **CFO**: Prioritizes transaction economics, margin stability, counterparty settlement timing, and liquidity buffers.
     - **COO**: Prioritizes payment rail reliability, dependency failover procedures, and partner uptime SLAs.
     - **Product**: Prioritizes checkout conversion rates, feature delivery roadmaps, and competitive feature parity.
4. **Hard Invariant: Material Response Divergence**:
   - Evaluated on identical signal fixtures: querying all 7 intents generates mutually distinct response texts, distinct structures, and intent-tailored follow-up suggestions.
5. **API & Frontend Integration**:
   - `POST /api/v1/cil/query` supports automatic intent classification or explicit intent override, logging intent to product and usage events.
   - `CILQueryResponse` returns the detected `intent`.
   - `CILPanel` displays the intent badge and expands inquiry suggestions across explain, relevance, evidence, and decision intents.

## Verification

- **Targeted Unit Tests**: 7/7 passed in `backend/tests/unit/test_cogent_intent_router.py`:
  - Canonical intent regex and semantic pattern classification across all 7 intents.
  - Explicit intent override and fallback handling.
  - Intent label formatting for executive UI presentation.
  - **Material Divergence Test**: Exact same NIBSS signal fixture queried with 7 distinct questions verified to yield:
    - 7 mutually distinct answer texts (`len(unique_texts) == 7`).
    - Distinct follow-up suggestion sets.
    - Intent-specific content assertions for every intent.
  - **Role-Awareness Test**: CFO vs COO vs Product on identical event produces mutually distinct, role-specialized answers.
  - `answer_query` async generation preserves intent and grounded citations.
  - `query_cil` API endpoint contract with auto-classification, explicit intent override, session updates, and analytics recording.
- **Combined Regression Suite**: 43/43 passed:
  - Track 1: `test_product_correction_relevance.py` (14 passed)
  - Track 2: `test_evidence_normalization.py` (11 passed)
  - Track 3: `test_cogent_intent_router.py` (7 passed)
  - Phase 3 API: `test_phase3_api.py` (11 passed)
- **Code Standards & Linter**: `ruff check` passed cleanly with 0 errors across `app/cil`, `api/v1/cil.py`, and tests.
- **Frontend Typecheck**: `npm run type-check` passed with 0 errors (`tsc --noEmit`).
- **Frontend Unit Tests**: All 33 Vitest tests passed (`npm run test:unit`).

## Next Steps

With Track 3 verified, the project sequence advances to **Track 4 — Investigation threads** (persisting multi-turn investigation context across user/tenant, origin object, messages, citations, findings, and unresolved questions).
