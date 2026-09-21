# MVP product correction - Track 4: Investigation Threads

Status: Verified locally; ready for staging deployment.

## Overview

Cogent is designed as an executive intelligence analyst that conducts bounded investigations across external events and company context. Prior to Track 4, CIL interactions operated as stateless, disconnected single-turn Q&A without tracking working findings, unresolved questions, cumulative citations, or multi-turn conversational continuity.

Track 4 implements:

1. **Database Schema & Migration**:
   - Alembic migration `backend/alembic/versions/0034_2026_09_21_investigation_threads.py`.
   - Adds `origin_type` (`VARCHAR(40)`), `origin_id` (`UUID`), `working_findings` (`JSONB`), and `unresolved_questions` (`JSONB`) to `cil.query_sessions`.
   - Backward-compatible default values (`'DECISION_BRIEF'` origin and `'[]'::jsonb` working lists).

2. **Investigation Thread Abstraction (`app/cil/threads.py`)**:
   - `InvestigationThread` data model with `session_id`, `tenant_id`, `user_id`, `origin_type`, `origin_id`, `title`, `status`, `messages`, `cumulative_citations`, `working_findings`, and `unresolved_questions`.
   - `ThreadMessage` representing turns with role (`user` / `assistant`), content, intent tag, and citations.
   - `format_history_for_prompt` method converting prior turns, established working findings, and unresolved questions into structured LLM context.
   - Persistence functions: `get_thread`, `create_thread`, `get_or_create_thread`, and `update_thread_state`.

3. **Multi-Turn Continuity & Synthesis (`app/cil/answering.py`)**:
   - Invariant verified on canonical test sequence:
     - **Turn 1**: *"How does this affect me as CFO?"* -> Classified as `RELEVANCE`; returns CFO margin stability, counterparty settlement timing, and liquidity buffer impact; establishes working finding on company transaction rails.
     - **Turn 2**: *"What about Moniepoint?"* -> Classified as `COMPARE`; benchmarks Moniepoint's POS agency volume against multi-rail redundancy; establishes peer profile finding; preserves Turn 1 context.
     - **Turn 3**: *"Which matters more?"* -> Continuation comparative query; synthesizes prior findings across company CFO margin exposure and Moniepoint positioning; establishes materiality verdict (internal margin stability takes priority over competitor volume).
   - `GroundedAnswer` generates intent-grounded `working_findings` and `unresolved_questions`.

4. **API Integration & Contract Preservation (`app/api/v1/cil.py`)**:
   - `POST /api/v1/cil/query`:
     - Seamlessly reuses existing session or initializes thread for the anchor object.
     - Passes thread history into `answer_query`.
     - Preserves exact 4-query database statement execution profile per turn, maintaining full backward compatibility with Phase 3 audit and billing contracts.
     - Returns `working_findings` and `unresolved_questions` alongside `answer_text`, `citations`, and `intent`.
   - `GET /api/v1/cil/sessions/{session_id}`:
     - Returns full `InvestigationThreadResponse` with chronological messages, deduplicated cumulative citations, working findings, and unresolved questions.

5. **UI Investigation Experience (`frontend/src/components/cil-panel.tsx`)**:
   - Maintains active `sessionId` across interactions so follow-up inquiries stay in the same thread.
   - Displays chronological turn sequence with intent tags and confidence indicators.
   - Displays working findings list and unresolved question chips for 1-click continuation.

## Verification

- **Targeted Unit Tests**: 4/4 passed in `backend/tests/unit/test_investigation_threads.py`:
  - `test_thread_model_creation_and_history_formatting`
  - `test_multi_turn_sequence_cfo_moniepoint_which_matters_more` (Canonical 3-turn CFO -> Moniepoint -> Which matters more sequence)
  - `test_thread_database_lifecycle` (Thread creation, retrieval, log aggregation, and deduplicated citations)
  - `test_get_investigation_session_endpoint` (Session retrieval and 404 handling)
- **Combined Regression Suite**: 47/47 passed:
  - Track 1: `test_product_correction_relevance.py` (14 passed)
  - Track 2: `test_evidence_normalization.py` (11 passed)
  - Track 3: `test_cogent_intent_router.py` (7 passed)
  - Track 4: `test_investigation_threads.py` (4 passed)
  - Phase 3 API: `test_phase3_api.py` (11 passed)
- **Code Standards & Linter**: `ruff check` passed cleanly (0 errors) across `backend/app/cil` and `backend/app/api/v1/cil.py`.
- **Frontend Typecheck**: `npm run type-check` passed with 0 errors (`tsc --noEmit`).
- **Frontend Unit Tests**: All 33 Vitest tests passed (`npm run test:unit`).

## Next Steps

With Track 4 verified, the implementation sequence advances to **Track 5 — Internal-first retrieval & evidence sufficiency decision**.
