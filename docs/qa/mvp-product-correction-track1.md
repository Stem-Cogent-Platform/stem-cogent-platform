# MVP product correction - Track 1

Status: implementation under verification; not yet deployed to staging.

## Relevance correction

Country and MARKET matches no longer establish meaningful relevance. Supported
company objects, explicit strategic priorities, and personal role concerns or
Focus Areas establish an explainable match. Geography supports personal scope;
it cannot qualify an item alone. Existing monitoring thresholds are unchanged.

Assessment rationale records the matching context, geography support, match
evidence strength, and decision posture. Personal monitoring retains its own
trace in additive migration `0033`. The briefing displays the explanation.
Match evidence strength is not intelligence confidence.

Readiness and visible projections reject historical country-only assessments
without deleting their data. A readiness exception cannot replace all meaningful
value. Personal matches stay scoped to the user and do not inflate company
invitation readiness. Reprocessing withdraws obsolete personal matches while
preserving history and stable identities.

## Verification

- 32 PostgreSQL/Redis integration tests passed, including country-only historical
  briefs/monitoring, supported company value, role/Focus Area persistence, user
  isolation, replay stability, Focus Area removal, and readiness exceptions.
  Log: `backend/_tmp_correction_track1_integration.log`.
- 30 targeted unit tests passed after the final persistence and projection edits.
- Earlier targeted engine/brief tests and full-backend Ruff passed.
- Mypy passed for all 114 application source files.
- Frontend typechecking and all 33 unit tests passed.
- Local test database upgraded from `0032` to `0033`, downgraded to `0032`,
  and upgraded again successfully.
- Full backend unit suite passed: 452 tests, with three existing Starlette
  deprecation warnings. Log: `backend/_tmp_correction_track1_full_unit.log`.
- Frontend lint passed with the same three pre-existing temporary-script warnings.
- Frontend CI passed. Full local integration suite and backend CI are pending.

## Read-only staging impact

Before deployment, migration remains `0032`. A bounded sample of the five most
recent company profiles contains 44 current, verified assessments. Seven retain
a supported company match; 37 fail the corrected company filter. Three of those
companies have no supported company assessments in the sample. These are
assessment counts, not deduplicated First Value counts or personal-match counts.
No staging rows were changed. Report:
`backend/_tmp_correction_track1_staging_impact.json`.

Fixtures run only against local `sc_test`; no synthetic staging intelligence was
created. Track 2 remains gated on Track 1 staging deployment and verification.

## Release and rollback

Deploy migration `0033` before the API/workers using Application CD's existing
migration step. It adds a JSONB column with an empty-object default and leaves
tenant RLS policies intact. An application rollback can leave the column in
place to retain match traces. Database downgrade is only rehearsed locally.

Staging deployment and authenticated product verification remain outstanding.
