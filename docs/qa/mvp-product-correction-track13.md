# MVP Product Correction — Track 13: Retention Delta & Freshness Separation

Status: Verified locally & fully tested; ready for staging and live deployment.

## 1. Overview

Per Track 13 of the MVP Product Correction Sequence (`docs/stem-cogent-mvp-product-correction-implementation-sequence.md`) and Sections 23 & 24 of `docs/stem-cogent-mvp-product-correction-spec.md`:

1. **Retention Delta Contract**:
   When an executive returns to Stem Cogent, the system must compute and clearly present the material changes since their previous session:
   - `new`: Total new verified developments matching their configured scope (`new_briefs + new_relevant_monitoring`).
   - `updated`: Existing intelligence assessments or briefs that changed materially (`updated_briefs`).
   - `escalated`: Number of briefs that escalated in decision posture (`escalated_count`).
   - `new_evidence`: Fresh verified evidence items attached to monitored developments (`new_evidence_items`).
   - `new_decision`: Material developments requiring explicit decision paths (`new_briefs`).

2. **Monitoring Freshness vs. Content Recency Separation**:
   Executives frequently conflate the freshness of the monitoring engine with the recency of incoming news. Track 13 cleanly decouples:
   - **System Freshness (`system_freshness_at` / `last_checked_at`)**: When the collection and monitoring pipeline last checked for updates (e.g., "System check: 4m ago").
   - **Content Freshness (`content_freshness_at`)**: When the latest verified real-world development occurred (e.g., "Latest verified development: 2h ago").
   - **User Delta**: Number of new items since their last visit watermark (`Since your last visit: X new developments`).

---

## 2. Code Changes

### 2.1 Backend Contract Extension (`backend/app/api/v1/product.py`)
- In `briefing_changes`, added calculation and response fields:
  ```python
  return jsonable_encoder({
      **row_dict,
      "new": new_briefs + new_monitoring,
      "updated": updated_briefs,
      "escalated": escalated_count,
      "new_evidence": new_evidence,
      "new_decision": new_briefs,
      "system_freshness_at": row_dict.get("monitoring_checked_at"),
      "content_freshness_at": row_dict.get("latest_relevant_at"),
      "since": since,
      "since_known": since_known,
      "as_of": window["as_of"],
      "enabled": True,
  })
  ```
- Provided sensible empty/disabled fallbacks when `PHASE5_BRIEF_LIFECYCLE_ENABLED` is false.
- Ensured `watchlist` endpoint defensive property access for `query_text` and `entity_id`.

### 2.2 Frontend UI Presentation (`frontend/src/app/briefing/page.tsx`)
- Extended `BriefingData["changes"]` type definition with retention fields:
  `new`, `updated`, `escalated`, `new_evidence`, `new_decision`, `system_freshness_at`, `content_freshness_at`.
- Updated the **Since your last visit** sidebar rail:
  - Header: displays total new developments or "Your first briefing visit" for initial sessions.
  - Granular breakdown:
    - `• X new decisions`
    - `• X assessments updated`
    - `• X escalated posture`
    - `• X new evidence sources`
- Updated the **Monitoring Freshness** panel:
  - Explicitly separates **System check** (`relativeTime(readiness.last_checked_at)`) from **Latest verified development** (`relativeTime(changes.content_freshness_at)`).

---

## 3. Verification & Test Coverage

### Automated Tests
- **Backend Unit Test**:
  - `backend/tests/unit/test_phase4_product_api.py::test_briefing_changes_retention_contract`:
    - Validates exact calculation of `new`, `updated`, `escalated`, `new_evidence`, `new_decision`, `system_freshness_at`, and `content_freshness_at`.
  - `backend/tests/unit/test_phase4_product_api.py::test_brief_lifecycle_flag_is_an_effective_rollback_gate`:
    - Validates disabled state schema with retention fields initialized to zero.
- **Frontend Type Safety**:
  - `npm run type-check`: passed with zero type errors.

All 6 unit tests in `backend/tests/unit/test_phase4_product_api.py` passed cleanly.
