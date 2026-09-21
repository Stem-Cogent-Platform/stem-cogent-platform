# MVP product correction — Track 0 baseline

Date: 2026-09-16. Governing documents: [product correction specification](../stem-cogent-mvp-product-correction-spec.md) and [Track 0–18 implementation sequence](../stem-cogent-mvp-product-correction-implementation-sequence.md).

Status: **COMPLETE**. Baseline checks passed before Track 1 implementation. No product correction is deployed.

## Repository and staging

- Canonical repository: `stem-cogent-platform`; no additional checkout created.
- Local branch: `feat/phase5-pilot-readiness`.
- Local HEAD: `3e483a13b46c2734c3de114d75ae59427e6b78ed`.
- Existing tracked and untracked Phase 5 changes are preserved. This HEAD alone does not identify the working implementation. Initial working-tree inventory: local `_tmp_correction_track0_worktree.txt`.
- Staging: `68624364d0f6b32f77aae9ad2102199f6432523f`, application CD `35012215042` succeeded. PR 104 accepts ordinary company descriptions without bypassing verified First Value.
- Live `/health/live`: `alive`; `/health/ready`: `ready`, PostgreSQL `ok`, Redis `ok`. These checks establish infrastructure health, not product acceptance.
- Direct source comparison against the staging archive matches all application, migration and frontend files after line-ending normalization. Only the pre-existing `backend/tests/unit/test_hash_width_migration.py` differs; bytecode is excluded. Local report: `_tmp_correction_track0_source_comparison.json`.
- The September 15 acceptance ledger is historical evidence; its country-based monitoring results do not satisfy the new correction contract.

## Current implementation paths

| Area | Existing path and behavior |
|---|---|
| Relevance | `backend/app/decision/engine.py`: deterministic assessment followed by role/domain/responsibility/Focus Area priority. Geography can establish applicability; MARKET objects can satisfy a context match. |
| Persistence and fanout | `backend/app/workers/tasks/decision.py`: tenant assessment, company monitoring, then personal ranking; existing queue and tenant scoping. |
| First Value | `backend/app/context/readiness.py`, `backend/app/intelligence/freshness.py`, and `backend/app/context/projections.py`: shared freshness, identity, evidence and match filters. `matched_sql` accepts any matched object or rule, including country-only matches. |
| Activation | `backend/app/workers/tasks/pilot_activation.py`: bounded recent canonical candidates, normal assessment worker, readiness and personalisation. |
| Evidence identity | `freshness.identity_sql`: source, canonical URL and material body identity, with signal identity fallback. Normalization handles volatile API counters; source-independence normalization remains a later track. |
| Cogent | `POST /api/v1/cil/query` → `cil.retrieve_context` → `cil.answering`. Retrieval dispatches by brief/signal/entity/company anchor. Query sessions/logs exist, but previous conversation is not supplied to retrieval. |
| Customer navigation | My Decision Briefing, Company Lens, Watchlist, Wider Intelligence, Alerts, Digests; Settings remains available. |
| Dossier and decisions | Existing `/signals/[signalId]` and `/briefs/[briefId]` routes. Preserve these routes and models while correcting their projections in the specified later tracks. |
| Other retained routes | `/briefing`, `/company`, `/intelligence`, `/watchlist`, `/entities/[entityId]`, `/search`, `/alerts`, `/digests`, `/settings`, onboarding/invitation/auth routes and internal admin routes. |

## Baseline validation

| Check | Current result |
|---|---|
| Frontend unit suite | 33 passed across four files. |
| Backend unit suite | **438 passed**, three pre-existing Starlette deprecation warnings, 907.63 seconds. The initial artificial per-test timeout was removed; all migration tests passed. Log: `backend/_tmp_correction_track0_unit.log`. |
| PostgreSQL integration | **53 passed**, 394.36 seconds, against existing local `sc_test` at migration `0032` and Redis. Fixtures retain runtime RLS and roll back. Initial missing-configuration failure is resolved. Log: `backend/_tmp_correction_track0_integration.log`. |
| Backend lint / whitespace | Ruff passes; `git diff --check` passes (line-ending advisories only). |
| Frontend type/lint/build | Passed. Production build completed all 30 static pages and dynamic routes. Lint has three pre-existing unused-variable warnings in temporary acceptance scripts, no errors. |
| Browser baseline | **18 passed**, 9.8 minutes, against the local production build and mocked API fixtures. Includes four responsive widths and cross-tenant denial. Initial approval-service usage block cleared; the sandboxed attempt timed out and was interrupted. Approved execution outside the sandbox passed without source changes. Log: `frontend/_tmp_correction_track0_browser_unrestricted.log`. |

No synthetic staging intelligence, readiness override, threshold reduction, production deployment, schema deletion or premium redesign was performed.

## Reproduced relevance defect

A read-only in-memory fixture with Nigeria as its only matched MARKET object scores **0.587**, exceeding the unchanged **0.450** monitoring threshold. It creates no decision in this case, but qualifies for monitoring. No fixture was inserted into staging or any database. Reproduction output: `backend/_tmp_correction_track0_country_reproduction.log`. This is the Track 1 negative control.

## Ordered continuation

Baseline complete. Implement Track 1 and its required negative/positive relevance cases. Deploy and verify Track 1 on staging before Track 2. Tracks 2–18 remain pending; HTTP success and earlier Phase 5 closure do not substitute for fresh CFO product acceptance.

## POST-PILOT BACKLOG

Retain the existing backlog in the September 15 acceptance ledger. No additional non-launch improvement is introduced by this baseline.
