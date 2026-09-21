# MVP Product Correction — Track 7: Live Evidence Lifecycle

Status: Verified locally; ready for staging deployment.

## Overview

Per Track 7 of the MVP Product Correction Specification (`docs/stem-cogent-mvp-product-correction-spec.md`, Section 17, and `docs/stem-cogent-mvp-product-correction-implementation-sequence.md`), live search evidence retrieved from external providers must not pollute the high-conviction intelligence base. 

Track 7 implements a deterministic, gated three-stage lifecycle for all live search evidence:
```text
EPHEMERAL  -->  INVESTIGATION_EVIDENCE  -->  PROMOTED_INTELLIGENCE
```

### Critical Invariant: No Automatic Promotion
External live search results can **never** bypass quality gates or automatically promote into global tenant intelligence. All search items begin as `EPHEMERAL` (used only for real-time context synthesis in Cogent) and can transition to `INVESTIGATION_EVIDENCE` when pinned or attached to an investigation thread. Transition from `INVESTIGATION_EVIDENCE` to `PROMOTED_INTELLIGENCE` requires an explicit promotion action accompanied by strict quality gate validation. Direct promotion from `EPHEMERAL` to `PROMOTED_INTELLIGENCE` is strictly prohibited and rejected.

---

## Architecture & Implementation

### 1. Lifecycle Engine (`backend/app/intelligence/live_search/lifecycle.py`)
- **`EvidenceLifecycleState` Enum**:
  - `EPHEMERAL`: Transient live result for answering; not saved to intelligence pool.
  - `INVESTIGATION_EVIDENCE`: Attached to a specific `InvestigationThread` (`cil.query_sessions`), persisting across session turns for continuity.
  - `PROMOTED_INTELLIGENCE`: Fully validated and elevated to tenant-level intelligence evidence.
- **Strict Transition Validator (`transition_lifecycle_state`)**:
  - Validates `EPHEMERAL -> INVESTIGATION_EVIDENCE` (thread attachment).
  - Validates `INVESTIGATION_EVIDENCE -> PROMOTED_INTELLIGENCE` (requires `QualityGateResult.passed == True`).
  - Prohibits backward transitions or illegal jumps (`EPHEMERAL -> PROMOTED_INTELLIGENCE` raises `LifecycleTransitionError`).
- **Quality Gate Engine (`validate_promotion_gates`)**:
  - **Gate 1 (Trusted Source)**: Checks source domain against recognized Tier 1 authorities (`cbn.gov.ng`, `nibss-plc.com.ng`, `sec.gov.ng`, `firs.gov.ng`, `naicom.gov.ng`, `ndic.gov.ng`) and accredited financial/fintech publications (`businessday.ng`, `techcabal.com`, `techpoint.africa`, `nairametrics.com`, `premiumtimesng.com`, `reuters.com`, `bloomberg.com`, `ft.com`, `semafor.com`).
  - **Gate 2 (Valid Publication Date)**: Enforces parseable ISO 8601 publication timestamp within allowed lookback window (default 365 days).
  - **Gate 3 (Substance)**: Rejects stub snippets under 40 characters or without meaningful content.
  - **Gate 4 (Deduplication)**: Verifies the canonical URL is not already present in the existing pipeline signal repository.

### 2. Database Schema Migration (`backend/alembic/versions/0035_2026_09_21_live_evidence_lifecycle.py`)
- Adds `attached_evidence JSONB NOT NULL DEFAULT '[]'::jsonb` to `cil.query_sessions`.
- Supports persistence of normalized live search evidence, lifecycle state metadata, quality gate evaluation logs, and timestamps directly on the investigation thread.

### 3. Investigation Thread Attachment (`backend/app/cil/threads.py`)
- Extends `InvestigationThread` dataclass with `attached_evidence: list[dict[str, Any]]`.
- Implements `attach_evidence_to_thread(thread, evidence_items)`:
  - Deduplicates incoming evidence by `canonical_id`.
  - Normalizes evidence to `INVESTIGATION_EVIDENCE` lifecycle state.
  - Preserves existing thread state, history, and citations.

### 4. Promotion API Endpoint (`backend/app/api/v1/cil.py`)
- Exposes `POST /api/v1/cil/sessions/{session_id}/evidence/{canonical_id}/promote`:
  - Enforces tenant isolation and permission role checks (`USE_CIL`).
  - Retrieves the investigation thread and locates target evidence by `canonical_id`.
  - Evaluates promotion gates against existing pipeline signal URLs.
  - Returns HTTP 422 with structured failure reasons if quality gates fail.
  - Updates the evidence lifecycle state to `PROMOTED_INTELLIGENCE` with promotion timestamp and audit metadata when passed.

---

## Test Verification

### Targeted Test Suite (`backend/tests/unit/test_live_evidence_lifecycle.py`)
All 6 tests passing:
1. `test_lifecycle_transition_valid_progression`: Verifies progression from `EPHEMERAL` to `INVESTIGATION_EVIDENCE` and on to `PROMOTED_INTELLIGENCE`.
2. `test_lifecycle_transition_forbids_automatic_promotion`: Asserts that attempting direct promotion from `EPHEMERAL` to `PROMOTED_INTELLIGENCE` raises `LifecycleTransitionError`.
3. `test_validate_promotion_gates_success`: Verifies full quality pass for trusted domains (e.g. `businessday.ng`) with valid publication dates and substantive snippets.
4. `test_validate_promotion_gates_failures`: Tests rejection for untrusted domains, missing/invalid dates, stub snippets (<40 chars), and duplicated URLs.
5. `test_attach_evidence_to_thread_lifecycle_management`: Verifies thread attachment promotes ephemeral items to `INVESTIGATION_EVIDENCE` and prevents duplicate entries.
6. `test_promote_investigation_evidence_api_endpoint`: Tests end-to-end API promotion flow, including HTTP 422 validation error on untrusted evidence and successful promotion on valid evidence.
