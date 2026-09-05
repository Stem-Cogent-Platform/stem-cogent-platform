# Phase 5 — bounded fresh-pilot acceptance, September 6, 2026

Tenant: `f0075fb0-3f6a-4d82-afbf-43932b425019` (Paystack, controlled staging).
Window started September 5 at 23:27:08 UTC / September 6 at 00:27:08 WAT.
Requested limit: 15 minutes. No production mutation or bulk queue replay.
Final evidence captured at 2026-09-05 23:40:40 UTC; completed within the requested window.

## A. Live acceptance matrix

PASS applies only to the stated evidence. FAIL means the acceptance gate is
unsatisfied or not yet demonstrated; it does not necessarily mean an endpoint
returned an error. Controlled tests are explicitly distinguished from live proof.

| Area | Gate | Evidence |
|---|---|---|
| Onboarding | FAIL | No accepted fresh user, Decision Lens, Focus Area or delivery preference at readiness snapshot |
| Invitation | FAIL | One pending invitation, zero accepted; invalid public token returns generic 400 |
| Company Context | PASS | Version 1, complete; Nigeria resolved, three products not requiring entity resolution; 4/4 objects resolved/not applicable |
| First Value Activation | FAIL | Two completed activation runs, but 0 briefs and only 2 structurally counted monitoring rows |
| Relevant Monitoring | FAIL | Both counted rows are index-page titles; neither has a stored publication date; not proven meaningful developments |
| Continuous Intelligence | FAIL | No new end-to-end legitimate signal/delivery journey demonstrated in this window |
| Decision Brief lifecycle | FAIL | Fresh tenant has no brief |
| Entity/evidence integrity | FAIL | Paystack endpoint returns 29 activity items; historical ingestion cleanup is still unproven |
| CIL | PASS, deployed diagnostic scope | Actual HTTPS endpoint: 200, grounded answer, one citation, OpenAI attribution; fresh user path not yet possible |
| OpenAI primary | PASS | `gpt-4.1-mini-2025-04-14`, 3,027 ms in persisted CIL query log |
| Groq fallback | PASS, controlled deployed-code fault | One simulated primary failure reached actual `openai/gpt-oss-120b`; valid cited answer |
| Embeddings | PASS, earlier funded probe | Prior bounded funded request returned 200; not repeated in this window |
| Alerts | FAIL | Fresh tenant has zero alerts and no completed qualifying delivery journey |
| Digests | FAIL | Fresh tenant has zero digests and no completed qualifying delivery journey |
| Team/admin boundary | PASS, targeted live checks | Tenant ADMIN gets 403; unauthenticated admin/auth routes get 401 |
| RLS/tenant isolation | FAIL, full gate unproven | Targeted live check passed: 2 other-tenant users become 0 under fresh-tenant runtime scope; only its profile visible. Full cross-resource journey remains open |
| Responsive UX | PASS, controlled browser tests | Seven product surfaces, no overflow at 1440/1024/768/390; 4 tests pass |
| Customer-copy cleanliness | FAIL, full live gate unproven | Real company display name is stored; complete fresh-user surface scan awaits accepted user |

## B. Intelligence integrity

Actual readiness SQL returns context version 1, four configured/resolved-or-not-
applicable objects, zero company briefs and two meaningful_monitoring_count rows.
That structural label does not establish actual development quality:

| Monitoring ID | Stored title | Domain/event | Publication time |
|---|---|---|---|
| `60c536c1-70d4-43da-891d-bc6513ee3323` | News – Nigeria Data Protection Commission News Latest News | REGULATORY_POLICY / CIRCULAR_ISSUED | NULL |
| `793ccd49-9846-438c-83f9-3f0aa4cf13d9` | Keep Track of Circulars - Securities and Exchange Commission, Nigeria Keep Track of Circulars Published: August 14, 2023 | REGULATORY_POLICY / CIRCULAR_ISSUED | NULL |

Each has one matched context object and four stored citations. Citation count
alone does not turn an index page into a new development. The deployed activation
query admits missing publication dates using detected_at, and the readiness
query checks field presence rather than index-page/event identity. These paths
explain how the observed rows can qualify structurally. Extraction/classification
must be traced against the source bodies before choosing the smallest repair.
Do not infer that the SEC page's 2023 title is a newly published 2026 event.

The regulatory-only distribution here is two stored regulatory classifications;
no artificial domain balancing was applied. No historical rows were consolidated,
deleted, or rewritten. No readiness override or artificial third item was added.

## C. AI and embedding checks

- Normal deployed CIL request passed through actual OpenAI, not deterministic
  fallback. This fixes the previously observed JSON-encoding failure.
- A separate one-shot staging process used the deployed answering code and real
  stored evidence. Primary fault injection called live Groq once, with retries
  disabled; citation validation passed.
- With both providers simulated unavailable in that isolated process, the answer
  remained deterministic and cited. No shared service configuration was changed.
- Fault testing is deployed-code evidence, not a claim of a browser-level fault
  injection or fresh-user authenticated journey.
- No paid embedding replay; no 7/30-day provider spend figures inferred from row
  counts. Existing longer-window cost evidence remains in the prior QA reports.
- Official OpenAI documentation was used to check the strict output contract:
  [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## D. Deployment and AWS cost safety

Staging commit `21d5d61`; migration `0028`. Application CD `33995462721` and
Infrastructure CD `33995462712` both succeeded. The serialized infrastructure
release applied **0 additions, 0 changes, 0 destroys**.

API revision 67 and frontend revision 55: completed rollout, 2/2 each.
Clustering revision 28: completed rollout, deliberately 0/0. No historical/DLQ
redrive, worker restoration, production deployment, budget change or claimed
savings. Existing provider usage ceilings, historical cleanup and AWS budget
threshold work are not closed by these smoke tests.

## E. Workspace and regression evidence

Canonical repo remains `stem-cogent-platform`. Existing user edits were preserved;
no folders or material files were deleted. Read-only/fault helpers are ignored
temporary local scripts. No credentials, invitation tokens or passwords were
printed or committed.

- 22 tests passed across live-acceptance, invitation, provisioning and auth-session
  suites (10.20 seconds).
- Four responsive Playwright cases passed (2.2 minutes), using controlled fixtures.
- Latest pre-release CI previously passed 363 tests, 75.48% coverage.

## F. Fresh-tenant transcript and task evidence

Provision: observed real company display name and complete profile.
Resolve: Nigeria is resolved; products are NOT_APPLICABLE, 4/4 ready.
Activate: two COMPLETED runs, version 1; no errors recorded.
First value: 0 briefs, 2 structurally counted index-page rows; gate fails.
Invite: one pending invitation; no accepted user at readiness sampling.
Accept/onboard/relogin: not demonstrated; no durable user/preferences yet.
Continuous intelligence, alert/digest and full security journey: not demonstrated.

Audit tasks:

- `0f69c7c1e0d74412a67f2e4176f4d2d5`: tenant inventory + deployed HTTPS CIL.
- `15088284b9d043c1aafb7edc9f301286`: live Groq fault path, both-down degradation,
  targeted read-only RLS checks.
- `aa312d066a1942f4a9fcbfec0edd1abc`: exact readiness SQL and monitoring trace.
- `2478528d46b141b0843825750603f141`: final read-only snapshot; unchanged pending
  invitation, zero users/preferences, and the same two index-page rows. All four
  audit tasks returned successfully and stopped; none is left polling.

## G. Verdict

**NOT READY — BLOCKERS REMAIN**

1. Fresh invitation acceptance and durable onboarding/relogin are not proven.
2. First-value quality is not satisfied: index pages count structurally, only two
   rows exist, and no company brief exists. Data quality must be repaired, not
   hidden with a readiness override.
3. The fresh continuous-intelligence/delivery/lifecycle and complete cross-resource
   isolation journey is still unproven; historical duplicate remediation remains
   open from the earlier acceptance repair.
