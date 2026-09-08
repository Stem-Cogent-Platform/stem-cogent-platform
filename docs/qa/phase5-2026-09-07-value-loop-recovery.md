# Phase 5 Value Loop Recovery — September 7, 2026

Status: staging acceptance remains blocked, continued September 8. Recovery
PR #93 deployed as `9c270643`, and runtime fix #94 deployed as `92a948f` in
successful CD run `34187332872`. Its audit verified migration `0029`, API
revision 70 and synthesis worker revision 36. The original fresh activation now
completes, but yields no qualifying First Value. Follow-up #95 deployed as `27275beb` in successful CD run `34191647816`
(completed September 8 06:33:07 UTC). Its normal MFA invitation rejection
was verified at 10:11:35 UTC. Synthesis revision 37 is at desired/running 1/1;
clustering revision 32 remains at its original 0/0.

Read-only staging tasks `0c05804c7ab940f387b00a1c96496598`,
`d220fb24480f44cf9f8ef7d577783798`, and
`cbf3c79f98b140a6af9738d0dddb4088` establish the baseline below. The first two
captured the exact pilot and deployed implementation before recovery edits.
All times below are UTC. No queues have been purged or replayed, and no
staging intelligence or pilot state has been fabricated for this report.

## A. Root cause matrix

Observed causes describe the pre-recovery baseline unless dated otherwise.

| Symptom | Observed cause | Recovery implementation |
|---|---|---|
| Empty first briefing | Paystack tenant `f0075fb0-3f6a-4d82-afbf-43932b425019` is at context version 6. Its three assessments belong to version 1; there are zero current-version assessments. Authenticated `/briefs` and `/relevant-monitoring` both return 200 with empty arrays. | Rebuild from all eligible canonical Global Outputs for the current company/lens version. Persist queued/running/completed/failed preparation state before dispatch; render preparation before counters. |
| Readiness bypass | The deployed invite handler checks only tenant existence. The pilot is labelled READY despite zero current value, with no narrow-scope override. | Authoritative server gate requires complete context, resolved/not-applicable objects, completed current-version activation, and one qualifying company brief or three unique meaningful monitoring items. A documented narrow-scope exception cannot bypass setup/activation. The admin UI displays the gate and disables invitations when it fails. |
| Activation freshness | Latest run `3505dfe6-e114-4df9-bebd-1a3b960aec30` used version 1 / 45 days, scanned three outputs, and counted two undated index pages as monitoring. Collection time had substituted for publication time. | Publication/event evidence determines eligibility. Unknown/future dates, discovery leads, index pages, duplicates, missing evidence, and unmatched assessments cannot establish First Value. Store exclusion counts and eligible date bounds. |
| 2023 content | The CBN corporate-name circular and redenomination release retained their 2023 source dates but appeared in a feed ordered by later synthesis time. Both were recollected on August 31, 2026. | Current/history/date-uncertain filters, publication ordering, explicit freshness labels, and historical dossier context. Collection and synthesis timestamps do not make old content current. |
| Personalisation | The deployed worker starts from existing current-version assessments; after onboarding advanced the profile version, its candidate set was empty. | Start from scoped canonical source outputs, assess the current company, then apply personal priorities. Request IDs prevent superseded jobs from completing the latest preparation. Focus changes advance the personal version. |
| Continuous intelligence | Scheduler and collectors are active. The CBN collector last completed at September 7 08:32:00.758126. Clustering is deliberately configured at desired/running 0/0; latest Global Output remains August 31 20:09:07. | Add a freshness guard before paid embedding/synthesis, preserve existing evidence, and retain tenant fan-out. Restoring and proving the existing worker remains a staging acceptance step. |
| Live badge | Connection state was presented as pipeline health. The client ignored monitoring events. | Neutral Monitoring wording; expose actual last collection time and listen for monitoring events. Use server change counts instead of incrementing a counter for every socket message. |
| Since Last Visit | The GET wrote visit telemetry, mixed company/personal copies, and could acknowledge updates before successful rendering. | Read-only snapshot GET; explicit post-render acknowledgement; canonical, current-context counts; material monitoring changes rather than verification timestamps. |
| Malformed Watchlist item | `and Invoicing` (`6f3f10ec-fb02-4b2a-8aee-bc787677164e`) was created by provisioning at September 5 23:17:33, before onboarding. A separate proper Invoicing object was added during onboarding. | Normalize leading list conjunctions at input and group canonical display labels. Derive activity from qualifying intelligence and links. Existing staging records are retained pending a separately evidenced repair. |
| Dossier missing/unreachable | The existing signal-detail architecture was absent from the deployed customer journey. | Restore `/signals/{signalId}` and its links; show global facts separately from current company interpretation, evidence, entities, related/historical intelligence, and the existing SIGNAL Cogent anchor. |
| Duplicate identity | The archived CBN API record contains `clickCount`; normalization included that counter in its content hash. Recollection could therefore change identity without changing source evidence. | Exclude popularity/transport metadata from new material hashes and canonically project legacy API variants without deleting stored rows. |
| Activation remains queued after dispatch | The real worker received the fresh activation, but its uncommitted candidate query ran for minutes under tenant RLS. Its plan repeatedly scanned the archive; the earlier administrative query timing did not validate this role. | Follow-up #94 drives from completed outputs with indexed lateral signal lookups and correlated citation checks. It commits RUNNING before inventory work, reapplies the tenant/runtime role, and persists failures with a 30-second query bound. The revised query took 0.170 seconds under `sc_app_runtime`, returning the same 122 canonical outputs. |

Pilot user `a155868f-b21e-4dca-bd8b-bb22e857b04e` is ACTIVE, has one Decision
Lens and two Focus Areas, and completed onboarding at September 6
05:16:40.866477. The invitation is ACCEPTED. The trial has no `started_at`.
The earlier onboarding UUID/text defect is repaired in the deployed release;
it is not the remaining cause of the empty current briefing.

## B. First Value

| Measurement | Existing staging pilot / corpus | Fresh recovery pilot |
|---|---|---|
| Activation scanned | Old activation scanned 3 | 122 canonical outputs |
| Fresh eligible | 333 raw rows canonicalize to 122 outputs | 1; 119 stale and 2 date-uncertain excluded |
| Meaningful monitoring | 0 for current context version 6 | 0 |
| Decision briefs | 0 current company briefs | 0 |
| Assessments created | Old assessments belong to version 1 | 1 at current version 1; score 0.065, no objects/rules matched |
| Readiness result | Current-version activation required despite old stored READY label | `NOT_READY_NO_RECENT_INTELLIGENCE`; invitation disabled |
| First user briefing | Authenticated APIs return empty arrays | Not reached: no qualifying value, invitation or trial start |

The user completed normal operator MFA sign-in in the acceptance browser.
Authenticated UI provisioning returned 201 for fresh tenant
`4282eb5f-1952-4230-bb9a-5973c7fdff88`, **Paystack (Recovery Acceptance)**, at
September 7 19:32:02 UTC. It starts PREPARING with no trial clock or invitation.
Controlled-staging notes were saved through the UI. The submitted list
`Online payments, Recurring payments, and Invoicing` created exactly three
properly named products. Deterministic resolution returned one RESOLVED market
and three NOT_APPLICABLE products, with no unresolved/ambiguous objects.

Normal UI activation returned 202 for run
`920f02b8-cbdf-4dcd-9066-59a82a5c42a6` at September 7 19:33:08 UTC, context
version 1, 45-day window. The initial worker exposed the RLS query defect.
After #94 deployed, synthesis was restored to desired 1 at September 8
05:32:29 UTC. The original queued message resumed automatically, with no
manual replacement, fabricated completion or DLQ replay. It ran from
05:32:58.620531 to 05:32:59.417409 UTC; Celery reported success in 1.095 seconds.
Its completion event was consumed and acknowledged.

Normal operator UI and read-only task `4780827304c941dba251fcaf902be572`
agree on COMPLETED, 122 scanned, 1 fresh eligible, 1 assessment, 0 briefs,
0 meaningful monitoring, 119 stale, 2 uncertain and 1 no-context-match.
The eligible date bounds are both August 12, 2026. The current assessment
`44d9f604-0d59-4af5-9b56-8af6b076a8ca` scores 0.065, with no matched objects,
rules or decision requirement. The gate returns
`NOT_READY_NO_RECENT_INTELLIGENCE` and the invitation button is disabled.

A direct request using the operator's normal refreshed MFA session exposed
a second response defect: a UUID in HTTPException detail turned the intended
409 into 500. #95 encodes both invite and manual READY rejection details and
tests their actual HTTP responses. After deployment, the same normal MFA
request returned HTTP 409 with `NOT_READY_NO_RECENT_INTELLIGENCE`, both value
counts zero and the activation ID serialized correctly. The UI button remains
disabled; no invitation was created and the trial clock has not started.

This fixture proves provisioning, list normalization, resolution, real worker
activation and empty-value gating. It does **not** satisfy the addendum's full
pilot proof: dependency, competitor and regulator context are not populated,
and no fresh Decision Lens/Focus Areas, onboarding, briefing or Cogent inquiry
has occurred. The provisioning UI supports dependencies and competitors but
has no regulator field. Context expansion remains acceptance work, and the
invitation/onboarding steps require sufficient real value. Public references
for a properly expanded Paystack scenario include its
[documented Wema Bank virtual-account support](https://support.paystack.com/en/articles/2124866),
[CBN licensing statement](https://support.paystack.com/en/articles/2131458),
and [Flutterwave's payment offering](https://flutterwave.com/ng/) (a candidate
competitor inferred from overlapping offerings, not a claim about Paystack's
own strategic priorities). These references have not been inserted as
customer-visible intelligence or used to change scoring.

Read-only feasibility task `04bdffe35aa24d518e4db66c28b91e3b` applied the new
canonical quality query to the existing staging corpus. Both 45- and 60-day
windows contain 122 canonical outputs and only one fresh, evidence-backed
candidate: CBN discount-window circular `6ced878e-9f7a-4a51-9f50-7fb47e35c42d`,
published August 12. Existing rules assess it at 0.465 for context version 6,
with no matched objects or applicability rules and no decision required.
It therefore supplies **zero qualifying First Value items** for this pilot.
No assessment or intelligence was written by this feasibility check.

The first staging-sized query hit its 25-second statement timeout because
citation validation cast indexed signal UUIDs to text. Validating and casting
the citation ID instead preserves the signal index and fails closed on invalid
IDs. The corrected 45-/60-day queries completed in 0.141/0.109 seconds.

Validation of the final recovery implementation:

- PR #93 merged as `9c270643` and deployed successfully in run `34132018488`.
  Its checks passed 391 backend unit tests, 24 integration tests, 75.32%
  coverage, 33 frontend unit tests, 16 browser tests, type checking, lint,
  migration checks, builds and security scans.
- Follow-up PR #94 merged as `92a948f1264f267a2dc5195c2c0494fc775e81db`.
  Backend CI `34169319408` passed 393 unit tests and 24 integration tests,
  with 75.45% coverage. The 34 targeted worker tests, mypy and Ruff also pass.
- With the user's PostgreSQL and Redis containers healthy, the final local
  value-loop and onboarding suites passed 23 tests in 97.98 seconds on
  September 8. Local migration head is `0029`; its upgrade/downgrade/re-upgrade
  checks passed. Earlier partial runs are superseded by completed checks.
- PR #95 CI `34191322053` passed 395 unit tests, 24 integration tests,
  75.51% coverage and security checks. The 10 local admin tests, Ruff and
  mypy with the CI configuration also pass.
- Encrypted pre-release RDS snapshot
  `sc-phase5-value-loop-staging-20260907` is available.

Recovery PR: https://github.com/Stem-Cogent-Platform/stem-cogent-platform/pull/93

Runtime follow-up: https://github.com/Stem-Cogent-Platform/stem-cogent-platform/pull/94

## C. Continuous intelligence

| Required evidence | Status |
|---|---|
| New signal processed after activation | Collection is active; new end-to-end recovery signal not yet proved |
| Tenant assessment created automatically | Activation created one current-context assessment; no new-source fan-out proved |
| Brief/monitoring updated automatically | Staging proof pending |
| WebSocket update | Client handler repaired; live proof pending |
| Since Last Visit | PostgreSQL read/acknowledgement tests pass; live return-visit proof pending |
| Alert/digest qualification | Existing qualification rules retained; new staging event not yet evaluated |
| End-to-end latency | Not measured; no acceptance latency is claimed |

The initial queue inventory included approximately 27,175 scored messages and
124,359 scored DLQ messages. These are point-in-time approximate counts, not
permission to replay the backlog. No production service has been changed.

Post-deployment audit `a2f09f0ff1184f82a11ca4e777a179b2` verified service
revisions. Runtime audit `17ace5a870bf4135b1359ac0bc4ed648` verified migration,
readiness, Watchlist, visit counts and dossiers. The current feed excludes the
old 2023 records; Watchlist displays one normalized Invoicing item with zero
qualified activity; Since Last Visit returns zero changes and an unknown first
visit without acknowledging anything.

Clustering task `769145bb400e4fea801d87f48a7552cc` ran the recovery image.
The intended five-minute probe's local watchdog ended during a session
interruption; actual task runtime was September 7 15:14:22–19:28:40 UTC.
The original desired count 0 was restored at 19:27:49 UTC and verified 0/0.
Saved samples contain 90 historical skips, one uncertain-date skip and no
sampled embedding errors; these are samples, not exhaustive totals. Synthesis
logs show duplicate skips and database connection-limit errors during this
interval. Database audit `ba0dcc96bce241f3b504cb003741ece1` found no new Global
Outputs since the probe began. This is not proof of zero embedding spend or
successful continuous intelligence.

The synthesis/decision service was restored to desired/running 1/1 on revision
36 after #94. Clustering is verified at its original 0/0 on revision 31.
No unbounded backlog replay is authorized or performed. Audit
`4780827304c941dba251fcaf902be572` still found zero new Global Outputs since
September 7 15:13:59 UTC.

Post-#94 read-only task `80b4242bd9d94ce8aa016215f88a8a7a` returned 200 for
health/live, health/ready, preparation readiness, changes, Watchlist, current
feed, historical search and both dossiers, in 0.045-0.226 seconds. This audit
used a bounded ordinary-user token inside ECS for the existing pilot; it is
not evidence of fresh-user onboarding or normal-user browser acceptance.

Recent-source inventory `372c5dbeba534b6088f5394bc4cab787` checked all public
rows dated within 45 days, excluding index pages and discovery leads:

| Type / classification | Stored rows | Distinct source URLs | Scored rows |
|---|---:|---:|---:|
| Feed items / no domain | 31,140 | 419 | 0 |
| API records / no domain | 8,888 | 12 | 0 |
| API records / REGULATORY_POLICY | 2,341 | 1 | 2,341 |

All 40,028 unclassified rows carry `CLASSIFICATION_REVIEW_REQUIRED`. The only
scored URL is the same August 12 CBN discount-window circular, repeatedly
collected; it is not new material intelligence. This is a classification
coverage/review bottleneck as well as a paused-clustering issue. The first
100-URL exploratory sample was alphabetically biased toward BusinessDay;
these grouped counts and the scored-only inventory supersede that sample.
No classification was forced and no thresholds or taxonomy were changed to
make a signal enter the acceptance pipeline.

## D. Dossier

| Required evidence | Status |
|---|---|
| Route | `/signals/[signalId]` builds; both authenticated staging detail APIs return 200 |
| Evidence | Stored, scoped source links; inaccessible citations fail closed |
| Historical context | 2023 dossier explicitly HISTORICAL; related historical list empty for inspected signals |
| Tenant relevance | No qualifying current interpretation for inspected signals; API returns null |
| Cogent anchor | Existing `SIGNAL` anchor retained; generation starts only on explicit inquiry |
| PASS/FAIL | API/evidence/freshness checks pass; full fresh-user dossier/Cogent acceptance FAIL (not reached) |

## E. Freshness

The raw CBN response is a 971,617-byte archive with SHA-256
`2cf94d8936768fa073d2ecd275fdac24dce0357052cd24805db8dcac931014ad`.
Its corporate-name record 7311 states `documentDate: 07/12/2023`, reference
`FPR/PRD/CIR/INT/001/003`. Its redenomination record 7272 states
`documentDate: 31/10/2023`, reference `CCD/INC/INT/001/022`.
There is no source update date in either archived record establishing a new
2026 development.

| Item | Published | Collected | Synthesized |
|---|---|---|---|
| Corporate-name circular, signal `932bd910-bbef-4c86-b7c6-0165e0958820` | 2023-12-07 | 2026-08-31 20:08:00.735741 | 2026-08-31 20:09:07.059576 |
| Redenomination release, signal `8cf8e2d5-c320-421c-afbe-de570b6d17e7` | 2023-10-31 | 2026-08-31 20:08:00.735741 | 2026-08-31 20:09:05.562995 |

The fix preserves the original evidence and labels it historical. Modification
dates without a supported material change remain metadata; GDELT discovery
timestamps remain discovery timestamps. Authenticated staging reads verified the repaired current feed excludes both
2023 records. The historical query and both stored signal dossiers return 200.

## F. Acceptance gate

Blockers remain: no qualifying fresh-pilot value; incomplete full pilot
fixture/journey; paused clustering and no new real source-to-assessment-to-
delivery update; no fresh-user return-visit, alert/digest or Cogent proof.
The invitation error-response fix #95 is deployed and its normal MFA 409
recheck passes. Recovery code tests, backup and #93/#94/#95 deployments are
completed, and synthesis is restored. Classification coverage/review blocks
431 recent source URLs from scoring; only one unique recent URL is scored. The corpus contains
legacy fallback summaries based on API metadata; their presence is not proof
of useful executive intelligence. No thresholds were lowered, no readiness
exception issued and no trial clock forced. UI/UX redesign and production
deployment remain outside this gate.

PHASE 5 VALUE LOOP NOT READY — BLOCKERS REMAIN
