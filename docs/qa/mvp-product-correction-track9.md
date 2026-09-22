# MVP Product Correction — Track 9: Decision Brief Contract & Structured Intelligence Engine

Status: Verified locally; ready for staging and live deployment.

## Overview

Per Track 9 of the MVP Product Correction Specification (`docs/stem-cogent-mvp-product-correction-spec.md`, Section 11, and `docs/stem-cogent-mvp-product-correction-implementation-sequence.md`), the Decision Brief projection and the Decision Brief UI (`/briefs/[briefId]`) have been refactored into the authoritative customer contract:

1. **Decision** (upfront required executive determination)
2. **Why now** (urgency catalyst, deadline, or material update trigger)
3. **What changed** (grounded verified development)
4. **Exposure** (company/tenant-specific exposure dimensions)
5. **Stakes** (financial, operational, and customer retention stakes)
6. **Decision Paths** (structured response options: Option A, Option B, etc.)
7. **Trade-offs** (comparative trade-off analysis across options)
8. **Validate next** (specific prerequisites and validation steps before execution)
9. **Unknowns** (residual uncertainties and information gaps)
10. **Owner / timing** (accountable role and target decision window)
11. **Evidence** (corroborated canonical citations and metrics)
12. **Investigate with Cogent** (interactive context-preserving entry bridge)

Furthermore, per executive product direction, this is not merely a cosmetic UI change:
Cogent's bounded intelligence analyst engine (`backend/app/cil/answering.py`), retrieval pipeline (`backend/app/cil/retrieval.py`), and backend API projection (`backend/app/intelligence/decision_brief.py`) formulate and reason across all 11 customer dimensions. When an operator asks Cogent "What action should we take?" or "What decision should we make?", Cogent structures its findings, trade-offs, validation steps, unknowns, and evidence across this exact framework.

---

## The 12 Dimensions of the Decision Brief Intelligence Contract

Every Decision Brief projection and deep decision inquiry adheres to this contract:

1. **Decision** — Upfront required executive determination, surfaced in a prominent decision banner with status pill (`DECISION REQUIRED`), not buried down the page.
2. **Why Now** — Explicit urgency driver:
   - High-urgency catalyst requiring immediate action cycle.
   - Active material update counts shifting baseline assumptions.
   - Verified market development confirmed across independent sources.
3. **What Changed** — Concise, verified event facts.
4. **Exposure** — Distinct company/tenant operational exposure categories (e.g., Settlement Liquidity, Payment Rail Dependency).
5. **Stakes** — Quantified financial float, operational risk, and customer conversion/retention consequences.
6. **Decision Paths** — Mutually exclusive response options mapped from verified response options (`MONITOR`, `ESCALATE`, `COMMUNICATE`, `REROUTE`).
7. **Trade-offs** — Comparative analysis evaluating immediate mitigation costs against delay exposure.
8. **Validate Next** — Concrete verification prerequisites before committing capital or operational resources.
9. **Unknowns** — Explicitly declared intelligence gaps, unconfirmed technical postmortems, or pending circulars.
10. **Owner / Timing** — Accountable executive role tailored to the user's Decision Lens (CFO, COO, Product) and target review window.
11. **Evidence** — Corroborated canonical source citations with independent source counts, primary source badges, and corroboration ratings.
12. **Investigate with Cogent** — Deep-dive action card with clickable prompt pills and full slide-over CIL panel carrying the brief context.

---

## Architectural Changes & Implementation

### 1. Decision Brief Projection Engine (`backend/app/intelligence/decision_brief.py`)
- **`DecisionBriefContract` Schema**: Strongly typed Pydantic model enforcing all contract fields.
- **`build_decision_brief_contract(...)`**:
  - Projects raw brief and assessment fields into structured contract dimensions.
  - Dynamically computes the **Why now** rationale based on urgency bands, material update counts, and decision windows.
  - Formats **Decision Paths** with explicit tradeoff bullet points.
  - Formulates distinct **Validate next** checklists and **Unknowns** lists.
  - Populates **Investigate with Cogent** with role-tailored entry prompts and 4 targeted inquiry pills.

### 2. Decision Brief API Endpoint (`backend/app/api/v1/product.py`)
- Updated `GET /api/v1/briefs/{brief_id}` to compute `brief_contract = build_decision_brief_contract(...)`.
- Passes normalized, deduplicated evidence and caller's `permission_role`.
- Injects `"brief_contract": brief_contract.model_dump()` into response while maintaining backward compatibility for legacy callers.

### 3. Cogent Analyst Intelligence & Retrieval Pipeline (`backend/app/cil/`)
- **`backend/app/cil/retrieval.py`**:
  - Updated `_retrieve_brief` SQL query to fetch `response_options`, `next_validation_steps`, `gaps_summary`, `material_change_count`, `decision_window`, and `brief_status`.
  - Packages these fields into `context["brief"]`.
- **`backend/app/cil/answering.py`**:
  - Refactored `CogentIntent.DECISION` in `deterministic_answer` to format answers using all 11 customer dimensions:
    - `Decision: ...`
    - `Why Now: ...`
    - `What Changed: ...`
    - `Exposure: ...`
    - `Stakes: ...`
    - `Decision Paths: ...`
    - `Trade-offs: ...`
    - `Validate Next: ...`
    - `Unknowns: ...`
    - `Owner / Timing: ...`
    - `Evidence: ...`
  - Maintains `Judgment:` and `Decision Support & Action Posture:` headers to ensure full backward compatibility with existing test suites.

### 4. Frontend Executive Decision Brief View (`frontend/src/app/briefs/[briefId]/page.tsx` & `types.ts`)
- Added `DecisionBriefContract` and `SourceMetrics` types to `frontend/src/lib/types.ts`.
- Refactored `/briefs/[briefId]` layout:
  - Header with relevance band, domain, and updated indicator.
  - Prominent **Decision Banner** (`00 Required Executive Decision`) with owner and timing callout.
  - Numbered sections in exact contract order:
    - `01 Why Now`
    - `02 What Changed`
    - `03 Your Exposure` & `04 What Is at Stake` (side-by-side split grid with chips)
    - `05 Decision Paths` (structured response option cards with tradeoff badges)
    - `06 Trade-offs` (comparative bullet points)
    - `07 What to Validate Next` (numbered prerequisites checklist)
    - `08 What Remains Unknown` (bulleted uncertainties list)
    - `09 Accountability & Timing` (definition list with owner role and decision window)
    - `10 Corroborated Evidence` (collapsible source drawer with tier badges and direct canonical links)
  - **Investigate Decision with Cogent** card with interactive inquiry pills that pre-populate and launch the CIL slide-over panel.
  - Decision context rail with status, confidence, context matches, and action execution buttons (`WATCH`, `ESCALATE`, `DISMISS`, `ACT`).

---

## Verification & Test Results

### 1. Unit Tests (`backend/tests/unit/test_decision_brief_contract.py`)
- `test_build_decision_brief_contract_all_dimensions`: Verified complete contract construction across all 12 dimensions.
- `test_decision_brief_why_now_variations`: Verified urgency triggers, material update triggers, and standard verified triggers.
- `test_decision_brief_fallback_paths_when_empty`: Verified bounded fallback response options (`MONITOR`, `ESCALATE`, `COMMUNICATE`) with trade-offs.
- `test_cogent_cil_decision_brief_answering_all_dimensions`: Verified that Cogent CIL produces answers with all 11 customer dimensions when responding to decision inquiries.
- **Result**: 4/4 PASSED.

### 2. Intent Router Regression Suite (`backend/tests/unit/test_cogent_intent_router.py`)
- Verified all 7 investigation intents (`EXPLAIN`, `RELEVANCE`, `EVIDENCE`, `COMPARE`, `IMPLICATION`, `DECISION`, `RESEARCH`) maintain distinct personas and backward compatibility.
- **Result**: 7/7 PASSED.

### 3. Frontend Compilation & Unit Tests
- `npm run type-check` (`tsc --noEmit`): PASSED with 0 TypeScript errors.
- `npm test` (`vitest run`): 4 test files passed, 33/33 tests PASSED.

### 4. Backend Linting
- `ruff check`: All checks passed.
