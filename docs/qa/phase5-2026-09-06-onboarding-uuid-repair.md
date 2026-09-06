# Fresh-pilot onboarding: UUID save failure

## TRACK B — reopened

Baseline: staging `21d5d61`, API revision 67, migration head `0028`.
Expected: final Delivery submission persists company objects, Decision Lens,
Focus Areas, delivery preferences and completion.
Observed: the founder screenshot at 00:49 Lagos shows the generic final-save
error with Important + Critical and Daily selected.

## Root cause and evidence

- CloudWatch `/sc/api-service/staging` contains nine matching `app.main` errors
  in three save attempts at 23:48:38, 23:48:54 and 23:49:15 UTC on September 5.
- Representative request: `1d33dc2f-712f-4ffb-b7b2-3d3ffa063f0d`.
- PostgreSQL raises `UndefinedFunctionError: operator does not exist: uuid = text`
  in `create_company_object`, before any Decision Lens or Focus Area request.
- The advisory-lock CTE casts the shared tenant parameter to TEXT; the same
  prepared-statement parameter is then compared against UUID columns.
- The wizard saves the profile first, then posts objects concurrently, then
  lens/focus/delivery. A completed earlier UI step is not proof of persistence.
- Read-only audit task `8fcd0f3bce4f40549b9f1e20517feb08` confirms tenant
  `f0075fb0-3f6a-4d82-afbf-43932b425019` has one accepted invitation and one
  ACTIVE tenant ADMIN, but no lens, focus, preferences or onboarding completion.
  Profile version advanced to 4 during retries. Four existing objects remain;
  current-version meaningful monitoring is zero. Invitation acceptance works.

## Fix applied

`backend/app/api/v1/context.py` acquires the advisory lock in a separate
statement using text-only lock parameters. The insert uses explicit UUID
casts for tenant/entity IDs. Acquiring the lock before the insert statement
also gives a waiting READ COMMITTED request a fresh snapshot for replay lookup.
Existing objects retain their IDs and values; replay does not bump the profile
version or append another object-created audit event.

No migration, provider invocation, queue replay, data deletion, production
deployment, or manual completion of the founder's onboarding is included.

## Tests and release status

- Local Ruff: PASS.
- Local targeted API and acceptance regression: 25 PASS.
- Five real PostgreSQL cases added under `tests/integration`: product,
  dependency and competitor creation/replay; daily and weekly final-save flows.
  They execute production endpoint SQL with the runtime RLS role, preserve
  permission/legal guards, and roll back fixture writes including endpoint
  commits. Only caches and personalisation dispatch are replaced.
- Local PostgreSQL unavailable because Docker Desktop's engine is not running.
- PR [91](https://github.com/Stem-Cogent-Platform/stem-cogent-platform/pull/91):
  CI and staging deployment pending. Do not mark the deployed defect fixed yet.
- Founder retry, refresh and relogin remain required after deployment. Existing
  first-value integrity and continuous-intelligence gates remain open.

Verdict: **NOT READY — BLOCKERS REMAIN**.
