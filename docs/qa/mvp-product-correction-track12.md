# MVP Product Correction — Track 12: Global Search & Ask Cogent Omnibox Contract

Status: Verified locally & fully tested; ready for staging and live deployment.

## 1. Overview

Per Track 12 of the MVP Product Correction Sequence (`docs/stem-cogent-mvp-product-correction-implementation-sequence.md`), `GOAL.md` (Section 4.2), and `stem-cogent-mvp-product-correction-spec.md` (Section 22):

1. **The Chrome Omnibox Paradigm**:
   - Upgraded passive search into an active **Search & Ask Cogent** omnibox:
     ```text
     Search intelligence or ask Cogent…
     ```
   - In Google Chrome, typing keywords brings up matching history/bookmarks, while typing questions or unfamiliar topics immediately offers a web search.
   - In Stem Cogent:
     - **Entity / keyword query** → returns categorized internal matches (Decision Briefs, Intelligence developments, and Entities) PLUS an instant option to investigate with Cogent.
     - **Question query** → automatically detects natural language intent (questions starting with *what, how, why, compare, can, does*, etc.) and pre-formats a tailored Cogent analyst investigation.
     - **Zero internal match / Insufficient stored data** → replaces dead-end empty states with an immediate **"Investigate Live with Cogent"** action that invokes live external search across verified sources.

2. **Full-Featured Analyst Investigation Canvas**:
   - Users can launch a bounded Cogent investigation directly from search without having to navigate to a specific dossier first.
   - The slide-over `CILPanel` opens side-by-side on `/search`, preserving context and allowing operators to ask multi-turn follow-up questions.

---

## 2. Code Changes

### 2.1 Top Navigation Search Input (`frontend/src/components/workspace-shell.tsx`)
- Upgraded the top navigation global search placeholder and aria-label to:
  `Search intelligence or ask Cogent…`
- Submitting any query of 2 or more characters immediately routes to `/search?q=...`.

### 2.2 Search API Endpoint (`backend/app/api/v1/search.py`)
- Added natural language question detection (`is_question: bool`).
- Added `cogent_inquiry` payload containing:
  - Formatted inquiry prompt.
  - Three tailored executive investigation angles (business model impact, competitor positioning, regulatory/compliance requirements).
- Selected `signal.id AS signal_id` on intelligence items to allow direct dossier navigation (`/signals/[signalId]`).
- Maintained complete backward compatibility with existing tests.

### 2.3 Bounded Query Context Auto-Binding (`backend/app/api/v1/cil.py`)
- Enhanced `query_cil` so that when `anchor_type == "COMPANY_LENS"`, `effective_anchor_id` automatically defaults to the caller's active tenant ID (`context.principal.tenant_id`).
- Allows global search queries to immediately anchor to the user's company context without requiring client-side tenant lookup.

### 2.4 Search & Ask Cogent Surface (`frontend/src/app/search/page.tsx`)
- Integrated Chrome-style omnibox input at the top of the search page.
- Rendered prominent **Ask Cogent** action card with 3 clickable suggested inquiry angles.
- If no internal records match, renders the **Live Search Fallback** banner prompting the user to investigate live across external sources.
- Integrated slide-over `CILPanel` allowing multi-turn analyst inquiries directly on the search page.

---

## 3. Verification & Test Coverage

### Automated Backend Tests
- `backend/tests/unit/test_ask_cogent_search.py`:
  - `test_search_detects_question_query_and_formats_cogent_inquiry`: Verifies question detection and suggested angle formatting.
  - `test_search_returns_signal_id_for_direct_dossier_navigation`: Verifies `signal_id` presence for direct dossier navigation.
- `backend/tests/unit/test_workspace_search.py`:
  - Verified tenant isolation and result grouping.
- **Full Backend Regression Suite**:
  - **81/81 tests passed** across all 13 regression test files.
  - `ruff check`: All checks passed.

### Automated Frontend Tests
- `frontend/src/app/search/search.test.tsx`:
  - Verified Search & Ask Cogent omnibox rendering and headers.
- **Full Frontend Vitest Suite**:
  - 8 test files, **43/43 tests passed**.
  - TypeScript type check (`tsc --noEmit`): **0 errors**.
