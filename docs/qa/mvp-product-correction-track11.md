# MVP Product Correction — Track 11: Remove Watchlist from Primary Customer Product

Status: Verified locally & fully tested; ready for staging and live deployment.

## 1. Overview

Per Track 11 of the MVP Product Correction Sequence (`docs/stem-cogent-mvp-product-correction-implementation-sequence.md`), `GOAL.md` (Section 7), and `stem-cogent-mvp-product-correction-spec.md` (Section 4.1):

1. **Watchlist Removed as a Standalone Primary Product**:
   - In Stem Cogent, the user should not have to maintain a separate manual Watchlist that duplicates known company context.
   - The primary navigation entry for `/watchlist` has been removed from `WorkspaceShell`.
2. **The New Monitoring Scope Paradigm**:
   ```text
   Company Context + Focus Areas = Monitoring Scope
   ```
   If the company already knows that Moniepoint is a competitor, NIBSS is an infrastructure dependency, and CBN is a regulator, the user does not need to "watch" them again manually. Continuous monitoring is automatically driven by this unified scope.
3. **Scope Moved to Company Lens (`/company`)**:
   - The **Company Lens** page now incorporates the **Active Monitoring Scope**, cleanly displaying:
     - **Competitors**: (e.g., Moniepoint, OPay, Flutterwave) with deep links to entity pages.
     - **Key Dependencies & Payment Rails**: (e.g., NIBSS, Interswitch, Providus Bank) with entity links.
     - **Monitored Products & Lines**: (e.g., POS Terminal Acquiring, Agency Banking).
     - **Personal Focus Areas**: (e.g., Merchant Profitability, Interchange Spread).
4. **Preserved Entity Pages & Backward-Compatible Redirects**:
   - Deep exploration via entity dossiers (`/entities/[entityId]`) remains fully operational.
   - Any legacy links or bookmarks pointing to `/watchlist` display an educational transition explaining the automated monitoring scope and immediately redirect the user to `/company`.
   - Backend APIs (`/api/v1/watchlist`) and database models remain intact for internal consistency.

---

## 2. Code Changes

### 2.1 Primary Navigation (`frontend/src/components/workspace-shell.tsx`)
- Removed `["/watchlist", "Watchlist", "watch"]` from the primary navigation array.
- The active primary navigation now contains:
  1. `My Decision Briefing` (`/briefing`)
  2. `Company Lens` (`/company`)
  3. `Intelligence` (`/intelligence`)
  4. `Alerts` (`/alerts`)
  5. `Digests` (`/digests`)

### 2.2 Company Lens Enhancement (`frontend/src/app/company/page.tsx`)
- Integrated `/api/v1/me/focus-areas` alongside `/api/v1/company/briefs`.
- Added the **Active Monitoring Scope** panel articulating:
  *"Stem continuously tracks external market changes matching your configured company dependencies, competitors, products, and personal focus areas. You do not need to maintain a separate manual watchlist."*
- Rendered categorized chips with entity cross-links (`/entities/[entityId]`) and direct shortcuts to adjust context in Settings.

### 2.3 Watchlist Educational Redirect (`frontend/src/app/watchlist/page.tsx`)
- Refactored `/watchlist` into an automated transition page.
- Directs users to `/company` via client-side routing while stating:
  *"Company Context + Focus Areas = Monitoring Scope"*.

### 2.4 Navigation Link Updates (`frontend/src/app/briefing/page.tsx`)
- Updated internal text links that formerly pointed to `/watchlist` to route to `/company`.

---

## 3. Verification & Test Coverage

### Automated Frontend Tests
- **Watchlist & Navigation Contract** (`frontend/src/app/watchlist/watchlist.test.tsx`):
  - Verified absence of `/watchlist` from `navigation` in `WorkspaceShell`.
  - Verified presence of canonical destinations: `/briefing`, `/company`, `/intelligence`, `/alerts`, `/digests`.
  - Verified educational notice on `/watchlist` stating `Company Context + Focus Areas = Monitoring Scope`.
  - Verified removal of manual watchlist tabs.
- **Company Lens Integration** (`frontend/src/app/company/company.test.tsx`):
  - Verified `CompanyPage` integration with monitoring scope and entity linkages.
- **Full Frontend Suite**:
  - 7 test files, **42/42 tests passed**.
  - TypeScript type check (`tsc --noEmit`): **0 errors**.

### Automated Backend Tests
- **Full Backend Regression Suite**:
  - **78/78 tests passed** across all 11 regression test files.
