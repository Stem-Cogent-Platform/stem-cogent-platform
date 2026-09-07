# Phase 5 Value Loop Recovery — September 7, 2026

Status: implementation and acceptance checks in progress. Local tests do not
establish staging acceptance. The staging release remains at `f1da8bb8`, API
revision 68, frontend revision 56, migration `0028` at the last live audit.

Read-only staging tasks `0c05804c7ab940f387b00a1c96496598`,
`d220fb24480f44cf9f8ef7d577783798`, and
`cbf3c79f98b140a6af9738d0dddb4088` establish the baseline below. The first two
captured the exact pilot and deployed implementation before recovery edits.
All times below are UTC. No queues have been purged or replayed, and no
staging intelligence or pilot state has been fabricated for this report.

## A. Root cause matrix

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

Pilot user `a155868f-b21e-4dca-bd8b-bb22e857b04e` is ACTIVE, has one Decision
Lens and two Focus Areas, and completed onboarding at September 6
05:16:40.866477. The invitation is ACCEPTED. The trial has no `started_at`.
The earlier onboarding UUID/text defect is repaired in the deployed release;
it is not the remaining cause of the empty current briefing.

## B. First Value

| Measurement | Existing staging pilot / corpus | Fresh recovery pilot |
|---|---|---|
| Activation scanned | 3 in the latest old activation | Not yet run |
| Fresh eligible | Public inventory has 333 completed non-dedup rows: 1 publication in 45 days, 325 older, 7 uncertain. This is a raw inventory count, not the new canonical quality gate. | Not yet measured |
| Meaningful monitoring | 0 for current context version 6; the old run's 2 index-page rows do not qualify | Not yet measured |
| Decision briefs | 0 current company briefs | Not yet measured |
| Readiness result | Stored READY is unsupported by current value | New server gate not deployed at last audit |
| First user briefing | Authenticated APIs return empty arrays | Normal MFA provisioning/invite/onboarding journey pending |

Local PostgreSQL: 21 cases passed in 47.75 seconds, including the actual personalisation worker
rebuilding assessments for a newer context version, tenant-isolated dossier
reads, invitation rejection/acceptance thresholds, freshness exclusions,
explicit visit acknowledgement, 60-day configuration, and final onboarding
persistence and legacy-counter/focus-version regressions.
Migration `0029` has been applied and rolled back/reapplied locally.
Ruff and mypy pass (114 application files). Bandit passes after review of
fixed SQL-fragment composition with bound request values; scoped B608 comments
document those cases. No scanner-wide rule or severity threshold changed.
Frontend CI passes type checking, lint, 33 unit tests, production build and
Playwright. The serial local rerun also passes all 16 browser tests, including
preparation/acknowledgement and WebSocket update counts. Earlier resource
timeouts are superseded by these completed runs. Full backend unit/coverage
and CI validation are still in progress.

Draft recovery PR: https://github.com/Stem-Cogent-Platform/stem-cogent-platform/pull/93
targets staging; it has not been merged or deployed.

## C. Continuous intelligence

| Required evidence | Status |
|---|---|
| New signal processed after activation | Collection is active; new end-to-end recovery signal not yet proved |
| Tenant assessment created automatically | Local worker regression passes; staging proof pending |
| Brief/monitoring updated automatically | Staging proof pending |
| WebSocket update | Client handler repaired; live proof pending |
| Since Last Visit | PostgreSQL read/acknowledgement tests pass; live return-visit proof pending |
| Alert/digest qualification | Existing qualification rules retained; new staging event not yet evaluated |
| End-to-end latency | Not measured; no acceptance latency is claimed |

The initial queue inventory included approximately 27,175 scored messages and
124,359 scored DLQ messages. These are point-in-time approximate counts, not
permission to replay the backlog. No production service has been changed.

## D. Dossier

| Required evidence | Status |
|---|---|
| Route | Local build includes `/signals/[signalId]` |
| Evidence | Stored, scoped source links; inaccessible citations fail closed |
| Historical context | Separate section and publication labels implemented |
| Tenant relevance | Current-context qualifying interpretation is separate from global facts |
| Cogent anchor | Existing `SIGNAL` anchor retained; generation starts only on explicit inquiry |
| PASS/FAIL | Staging acceptance pending; not a PASS |

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
timestamps remain discovery timestamps. The current staging feed has not yet
been verified with the repaired implementation.

## F. Acceptance gate

Pending: final checks, staging release/backup, bounded restoration of the
existing worker, normal MFA fresh-pilot journey, and post-activation live
evidence through notification and return-visit counts. UI/UX redesign and
production deployment remain outside this task.

PHASE 5 VALUE LOOP NOT READY — BLOCKERS REMAIN
