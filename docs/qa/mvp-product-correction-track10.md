# MVP Product Correction — Track 10: Intelligence Surface & Domain Stream Contract

Status: Verified locally & fully tested; ready for staging and live deployment.

## 1. Overview

Per Track 10 of the MVP Product Correction Sequence (`docs/stem-cogent-mvp-product-correction-implementation-sequence.md`), `GOAL.md` (Section 6), and `stem-cogent-mvp-product-correction-spec.md` (Section 3.2):

1. **Surface Renaming**:
   - Customer-facing **Wider Intelligence** has been renamed to **Intelligence** across all surfaces, top navigation, page headings, copy, search result groupings, and telemetry event names.
2. **Authoritative Domain Stream Contract**:
   - The surface presents **9 dedicated domain tabs**:
     - `For You` (`FOR_YOU`): Strongly personalized stream filtering verified developments matching company dependencies, competitors, products, active focus areas, and role Decision Lens.
     - `Regulatory` (`REGULATORY`): Central Bank of Nigeria (CBN) circulars, policy mandates, licensing conditions, NDIC/SEC/FCCPC supervision, and statutory compliance.
     - `Competition` (`COMPETITION`): Verified moves across Nigerian fintech rivals (e.g., Moniepoint, OPay, Flutterwave, PalmPay)—pricing shifts, agent banking expansion, merchant acquiring, and product rollouts.
     - `Infrastructure` (`INFRASTRUCTURE`): Payment rails, NIBSS switches, USSD routing, interbank settlement latency, and core banking uptime telemetry.
     - `Market & Customers` (`MARKET_CUSTOMERS`): Merchant adoption patterns, POS dispute trends, consumer wallet liquidity, and retail cash velocity shifts.
     - `Financial & Economic` (`FINANCIAL_ECONOMIC`): Monetary policy rate (MPR) hikes, foreign exchange volatility, card interchange yields, inflation, and treasury margin dynamics.
     - `Capital & Partnerships` (`CAPITAL_PARTNERSHIPS`): Venture funding rounds, debt facilities, M&A acquisitions, strategic sponsor bank tie-ups, and ecosystem alliances.
     - `Expansion` (`EXPANSION`): Cross-border payment corridors (PAPSS, regional remittances), Francophone/East Africa expansion, and new licensing verticals.
     - `Risk & Trust` (`RISK_TRUST`): Emerging fraud vectors, account takeover schemes, chargeback spikes, AML/KYC enforcement actions, and cyber posture.
3. **The "Facebook Tabs" Paradigm**:
   - Rather than simple cosmetic or superficial database filters, each tab operates like a dedicated domain stream. When an executive opens a tab (e.g. CFO clicking *Financial & Economic*, CEO clicking *Competition*, Compliance Lead clicking *Regulatory*), they are presented with:
     - Clear stream purpose banner and executive focus guidelines.
     - Time period filtering (`Current and recent`, `Historical context`, `Date unconfirmed`, `All`).
     - Priority filtering (`Priority only (High & Critical)`).
     - Full-text search scoped to the domain.
     - Verified intelligence cards displaying decision posture (`⚡ DECISION REQUIRED`), urgency badges, company object relevance callouts (`🎯 Relevant to: Moniepoint (Competitor)`), and executive relevance rationales.
4. **Context-Preserving Entry Point**:
   - Every card provides two primary actions:
     - `View dossier →` linking directly to `/signals/[signalId]`.
     - `Investigate with Cogent 🔍` opening a slide-over analyst panel anchored to that signal, pre-populated with role-informed inquiry angles.

---

## 2. Backend Implementation Details

### 2.1 API Endpoint Enhancements (`backend/app/api/v1/product.py`)
- **Query Parameter**: Added `tab: str = Query(default="ALL")` to `wider_intelligence` (`/api/v1/signals` and `/api/v1/intelligence`).
- **Domain Mapping**:
  - `REGULATORY` → `['REGULATORY_POLICY']`
  - `COMPETITION` → `['COMPETITIVE_PRODUCT']`
  - `INFRASTRUCTURE` → `['INFRASTRUCTURE_RELIABILITY', 'INFRASTRUCTURE_INCIDENTS']`
  - `MARKET_CUSTOMERS` → `['CUSTOMER_MARKET', 'MARKET_CUSTOMERS']`
  - `FINANCIAL_ECONOMIC` → `['FINANCIAL_ECONOMIC']`
  - `CAPITAL_PARTNERSHIPS` → `['CAPITAL_PARTNERSHIP', 'CAPITAL_PARTNERSHIPS']`
  - `EXPANSION` → `['MARKET_EXPANSION', 'EXPANSION']`
  - `RISK_TRUST` → `['FRAUD_RISK_TRUST', 'RISK_TRUST']`
- **Personalized `FOR_YOU` Filtering**:
  Filters for items with `assessment.relevance_score >= 0.45` OR matched company objects (`cardinality(assessment.matched_object_ids) > 0`) OR `decision_required IS TRUE`.
- **Enriched Assessment Projection**:
  Returns `relevance_score`, `relevance_band`, `decision_required`, `decision_type`, `matched_company_objects`, and `why_relevant`.
- **Telemetry Events**:
  Registered `INTELLIGENCE_VIEWED` and `INTELLIGENCE_TAB_CHANGED` in product analytics.

---

## 3. Frontend Implementation Details

### 3.1 Intelligence Page (`frontend/src/app/intelligence/page.tsx`)
- Renamed page header to `Intelligence`.
- Added the 9 canonical tabs (`INTELLIGENCE_TABS`) with icon, label, description, and `operatorFocus`.
- Rendered dynamic domain stream context banner describing the domain and highlighting the Executive Lens.
- Rendered intelligence cards with:
  - Decision required flag (`⚡ DECISION REQUIRED`).
  - Matched company objects chip (`🎯 Relevant to: ...`).
  - Executive relevance rationale (`Why it matters`).
  - Primary source badge, published date, and detection date.
  - One-click `Investigate with Cogent 🔍` button.
- Integrated slide-over `CILPanel` for bounded analysis without leaving the stream.

### 3.2 Navigation & Surface-Wide Renaming
- `frontend/src/components/workspace-shell.tsx`: Updated navigation label to `Intelligence`.
- `frontend/src/app/signals/[signalId]/page.tsx`: Updated back link to `← Intelligence`.
- `frontend/src/app/search/page.tsx`: Updated search group title to `Intelligence`.
- `frontend/src/app/digests/page.tsx`: Updated selection label to `Selected Intelligence`.
- `frontend/src/app/briefing/page.tsx`: Updated CTAs to `Review Intelligence` and `Explore Intelligence`.

---

## 4. Verification & Test Coverage

### Automated Backend Tests
- `backend/tests/unit/test_intelligence_surface.py`:
  - `test_wider_intelligence_default_tab_all`: Verifies all items returned under default `ALL`.
  - `test_wider_intelligence_regulatory_tab`: Verifies strict taxonomy filtering to `REGULATORY_POLICY`.
  - `test_wider_intelligence_infrastructure_tab`: Verifies taxonomy filtering to `INFRASTRUCTURE_RELIABILITY` and `INFRASTRUCTURE_INCIDENTS`.
  - `test_wider_intelligence_for_you_personalization`: Verifies relevance score and matched object filtering.
- **Full Backend Regression**: 78/78 tests passed.
- **Linter**: `ruff check` passed with zero errors.

### Automated Frontend Tests
- `frontend/src/app/intelligence/intelligence.test.tsx`:
  - Verifies exact 9 canonical tabs match GOAL.md and Track 10 specification.
  - Verifies tab descriptions and operator focus strings.
  - Verifies domain stream mappings for Regulatory, Infrastructure, and Financial & Economic.
- **Full Frontend Regression**: 38/38 tests passed.
- **TypeScript Type Check**: `tsc --noEmit` passed with zero errors.
