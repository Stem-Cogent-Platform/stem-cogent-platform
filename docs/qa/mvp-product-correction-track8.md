# MVP Product Correction — Track 8: Dossier Contract & Cogent Structured Intelligence

Status: Verified locally; ready for staging deployment.

## Overview

Per Track 8 of the MVP Product Correction Specification (`docs/stem-cogent-mvp-product-correction-spec.md`, Section 10, and `docs/stem-cogent-mvp-product-correction-implementation-sequence.md`), the Signal Dossier has been upgraded from a passive database inspector into an authoritative, 12-section intelligence memo. 

Furthermore, per executive product direction, this is not merely a visual UI update: Cogent's bounded intelligence analyst engine (`backend/app/cil/answering.py`) and API projections have been refactored so that when an executive inquires about a development or enters an investigation, Cogent structures its findings, uncertainties, relevance, and recommendations according to this exact 12-part intelligence framework.

---

## The 12-Section Dossier Intelligence Contract

Every dossier projection and deep signal investigation adheres to this contract:

1. **Judgment** — One concise, authoritative intelligence verdict for executive leadership.
2. **What Changed** — Verified event facts, involved parties, effective dates, and actions taken.
3. **Why It Matters to You** — Specific relevance calculated against Company Context and the user's Decision Lens (CFO, COO, Product, Risk/Compliance).
4. **Exposure** — Only supported exposure categories (e.g., Margin Compression, Rail Reliability, Settlement Delay, Regulatory Penalty).
5. **Implications** — Plausible first- and second-order operational and financial consequences.
6. **Decision Posture** — Authoritative operational stance: `NO_ACTION`, `MONITOR`, `INVESTIGATE`, or `DECISION_REQUIRED`.
7. **What We Know** — Corroborated, evidence-backed facts verified across canonical sources.
8. **What We Do Not Know** — Explicitly declared intelligence gaps, unconfirmed technical details, and pending circulars.
9. **Related Intelligence** — Materially correlated signals and peer market movements.
10. **Historical Context** — Precedents, previous regulatory circulars, and chronological timeline.
11. **Sources** — Citation-first evidence list with independent source count and Tier 1/2 credibility badges.
12. **Investigate with Cogent** — Context-preserving entry bridge with pre-populated, role-specific follow-up questions.

---

## Architectural Changes & Implementation

### 1. Dossier Projection Engine (`backend/app/intelligence/dossier.py`)
- **`DossierIntelligenceContract` Schema**: Strongly typed Pydantic model enforcing the 12 sections.
- **`build_signal_dossier_contract(...)`**:
  - Deterministically evaluates signal facts, tenant interpretations, and deduped evidence.
  - Tailors the "Why It Matters to You" text specifically to the user's Decision Lens:
    - **CFO**: Unit margins, transaction economics, interchange yields, liquidity buffers.
    - **COO**: Rail uptime, failover SLAs, routing resilience, incident response.
    - **Product**: Checkout conversion rates, feature delivery timelines, competitive parity.
    - **Risk/Compliance**: Supervisory obligations, reporting mandates, licensing exposure.
  - Derives the **Decision Posture** deterministically:
    - `DECISION_REQUIRED` when company assessment mandates immediate action.
    - `INVESTIGATE` when relevance score >= 0.70 or urgency is `HIGH`.
    - `MONITOR` when relevance score >= 0.45 or urgency is `MEDIUM`.
    - `NO_ACTION` otherwise.
  - Formulates distinct lists for **What We Know** (verified developments) and **What We Do Not Know** (missing circulars or implementation guidelines).
  - Populates **Investigate with Cogent** payload with role-specific entry prompts and four targeted inquiry buttons.

### 2. Signal API Endpoint (`backend/app/api/v1/product.py`)
- Refactored `GET /api/v1/signals/{signal_id}` to call `build_signal_dossier_contract`.
- Injects the caller's `permission_role` into the contract builder.
- Returns `"dossier": contract.model_dump()` in the response while maintaining backward-compatible top-level fields for existing consumers.

### 3. Cogent Analyst Intelligence & Response Persona (`backend/app/cil/answering.py`)
- Enhanced `_INTENT_INSTRUCTIONS` with instructions guiding LLM generation into structured intelligence memo dimensions (Judgment, What Changed, Relevance, Exposure, Decision Posture, What We Know vs. What We Do Not Know).
- Enhanced `deterministic_answer` to format `EXPLAIN`, `RELEVANCE`, and `DECISION` outputs with explicit structured intelligence headers while preserving strict string assertion compatibility with existing router tests.

### 4. Frontend Executive Dossier View (`frontend/src/app/signals/[signalId]/page.tsx`)
- Refactored `/signals/[signalId]` into an executive intelligence briefing memo:
  - **Verdict Header**: Intelligence Judgment callout with Decision Posture badge (`DECISION_REQUIRED`, `INVESTIGATE`, `MONITOR`, `NO_ACTION`).
  - **Relevance & Exposure Card**: Role-tailored "Why It Matters to You" with exposure tags.
  - **Fact vs. Uncertainty Grid**: Two-column comparison of "What We Know (Verified Facts)" vs. "What We Do Not Know (Gaps & Uncertainties)".
  - **Evidence & Corroboration Panel**: Citation-first source list showing independent source count, publisher tiers, and publication dates.
  - **Context & Timeline**: Chronological historical context and related intelligence links.
  - **Investigate with Cogent Action Bar**: Pre-composed prompt with one-click inquiry pills that immediately wire into the interactive Cogent drawer.
- Updated `CILPanel` (`frontend/src/components/cil-panel.tsx`) to accept `initialPrompt` and `suggestedInquiries` props.

---

## Test Verification

1. **Targeted Dossier Contract Test Suite (`backend/tests/unit/test_dossier_contract.py`)**: 4/4 passed:
   - `test_build_signal_dossier_contract_all_12_sections` (All 12 sections verified)
   - `test_dossier_contract_role_differentiation` (Role-specific relevance for CFO, COO, Product)
   - `test_dossier_decision_posture_derivation` (Deterministic posture logic)
   - `test_dossier_what_we_know_and_do_not_know_separation` (Fact vs. uncertainty separation)

2. **Full Regression Suite across Tracks 1–8**: 54/54 passed:
   - Track 8 dossier contract: 4 passed
   - Track 7 evidence lifecycle: 6 passed
   - Track 6 live search: 7 passed
   - Track 1 relevance & company matching: 14 passed
   - Track 2 evidence normalization & metrics: 11 passed
   - Track 3 intent router & bounded answering: 7 passed
   - Track 4 investigation threads: 4 passed
   - AWS Terraform secret wiring: 1 passed

3. **Static Analysis & Linting**:
   - `ruff check` passed with 0 errors across all modified backend files.

4. **Frontend TypeScript Compilation**:
   - `npm run type-check` (`tsc --noEmit`) passed with 0 errors.
