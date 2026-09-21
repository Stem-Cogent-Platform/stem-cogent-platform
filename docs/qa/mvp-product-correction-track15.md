# MVP Product Correction — Track 15: Company Transparency (Unified Organizational Model)

Status: Verified locally & fully tested; ready for staging and live deployment.

## 1. Overview

Per Track 15 of the MVP Product Correction Sequence (`docs/stem-cogent-mvp-product-correction-implementation-sequence.md`) and Sections 14, 15, 27, 30 & 32 of `docs/stem-cogent-mvp-product-correction-spec.md`:

1. **Unification of Company Lens & Company Context**:
   - The previously fragmented concepts of "Company Lens" and "Company Context" are consolidated into a single, cohesive customer concept: **Company** (`/company`).
   - The primary navigation and page header present this as **Company** under the eyebrow *"Organizational Model & Scope"*.

2. **Radical Operational Transparency (No Vanity Charts)**:
   - Eliminates decorative or vanity charts, meaningless graphs, and synthetic activity heatmaps.
   - Replaces them with dense, actionable, transparent operational modeling:
     - **Business Categories & Context Version**: Exact taxonomy classification and schema watermark.
     - **Operating Markets**: Geographic and jurisdiction boundaries.
     - **Strategic Priorities**: Configured corporate focus items directly informing relevancy ranking.
     - **Full Monitored Scope Grid**:
       - *Competitors* (e.g., Moniepoint, OPay, Flutterwave) with direct `/entities/[entityId]` links.
       - *Regulators & Authorities* (e.g., CBN, SEC, NFIU) with direct `/entities/[entityId]` links.
       - *Dependencies & Rails* (e.g., NIBSS, Interswitch, AWS) with direct `/entities/[entityId]` links.
       - *Partners & Counterparties* with direct entity links.
       - *Products & Service Lines* (e.g., POS terminal acquiring, merchant acquiring).
       - *Personal Focus Areas* (role-specific inquiry lenses).
     - **Company Decisions**: Open Decision Briefs requiring executive alignment across the leadership team.

---

## 2. Code Changes

### 2.1 Company Surface Refactoring (`frontend/src/app/company/page.tsx`)
- Renamed page heading:
  - Eyebrow: `Organizational Model & Scope`.
  - Title: `Company`.
  - Lead description: *"Your shared organizational model, strategic priorities, and active monitoring scope. Stem continuously tracks these counterparties and market dependencies on behalf of your leadership team."*
  - Top action: `View My Briefing` routing to `/briefing`.
- Scope Grid Expansion:
  - Added dedicated blocks for **Regulators & Authorities** (`REGULATOR`) and **Partners & Counterparties** (`PARTNER`).
  - Added entity links (`/entities/[entityId]`) with external link indicators (`↗`) across all counterparties.
  - Retained strict zero-vanity-chart policy: pure semantic structure, status chips, and real Decision Brief cards.

### 2.2 Test Suite Updates (`frontend/src/app/company/company.test.tsx`)
- Updated mock data to include `REGULATOR` (CBN) and `PARTNER` (Interswitch) alongside `COMPETITOR`, `DEPENDENCY`, and `PRODUCT`.
- Validated clean rendering and scope integration.

---

## 3. Verification & Test Coverage

### Automated Tests
- `npm test src/app/company/company.test.tsx`:
  - 1/1 passed in 10.13s.
- `npm run type-check`:
  - Passed with zero errors.
