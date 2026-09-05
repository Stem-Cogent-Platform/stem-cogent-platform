# Phase 5 live follow-up — 2026-09-05

This report supersedes the September 4 access-blocked conclusions. AWS staging,
production, and payer identities now authenticate. Production was not mutated.
No historical data was deleted, no queue was redriven, and the documented
clustering pause was preserved. Credentials and tokens were kept out of output.

## A. Live baseline and acceptance

- Staging account: `437040615141`; payer: `271791847185`.
- Application/worker/frontend image tag: `dc4755b436508d19535ed414abd5090c5a2a4ac5`.
- Successful Application CD: `33866430066`.
- Live Alembic head: `0027`; candidate head: `0028`.
- All six Phase 5 flags are enabled in staging.
- API/frontend: `2/2`; seven enabled workers: `1/1`; clustering: `0/0`.
- RDS: `sc-postgres-staging`, available, Multi-AZ `db.t4g.large`, 100 GiB,
  seven-day backup retention; latest restorable time at inventory: 04:57:31 UTC.
- Database/API audit task: `782f74eb9d61453280256da93a5eca48`.
- Integrity audit task: `6f7ce66aadef4768ac6b5cc4274d4e7a`.

Live health and authenticated context, briefing, monitoring, entity-related
navigation, alerts, digests, team and billing GETs respond. A normal tenant
principal receives 403 from the internal tenant-administration route. These
checks do not prove the fresh-tenant acceptance journey.

| Acceptance area | Result | Evidence/limitation |
|---|---|---|
| Onboarding | FAIL | Candidate repair not deployed; final completion/relogin not tested |
| Invitation | FAIL | No fresh invitation journey in this run |
| Company Context | FAIL | Active profile is version 6; visible monitoring/activation remains version 1 |
| First Value Activation | FAIL | Prior run counted 4,338 signals; corrected candidate selects only three recent distinct outputs |
| Relevant Monitoring | FAIL | 4,560 rows, 4,338 signal IDs, only 76 source/URL/hash identities; all regulatory circulars |
| Continuous Intelligence | FAIL | 75,634 signals in prior 24h, zero new Global Outputs, clustering paused |
| Decision Brief lifecycle | FAIL | Zero stored briefs; no live lifecycle proof |
| Entity/evidence integrity | FAIL | Paystack contains 4,703 signal IDs for 29 content identities |
| CIL | FAIL | Controlled live query returns HTTP 500; API role cannot resolve provider secrets |
| OpenAI primary | FAIL | Embedding probe returns 429, insufficient_quota, credit_balance_exhausted |
| Groq fallback | FAIL | Candidate timeout→Groq probe passed in staging; deployed API access/routing remains uncorrected |
| Embeddings | FAIL | 11,297 stored vectors for 145 distinct input hashes; current provider cannot embed |
| Alerts | FAIL | Zero stored alerts; qualifying delivery not exercised |
| Digests | FAIL | Zero stored digests; qualifying delivery not exercised |
| Team/admin boundary | FAIL | Tenant-to-internal 403 verified; complete role/mutation matrix still open |
| RLS/tenant isolation | FAIL | Candidate SELECTs executed under runtime role; full cross-tenant mutation test still open |
| Responsive UX | PASS | Prior local responsive run at 1440/1024/768/390 retained; frontend unchanged this turn |
| Customer-copy cleanliness | FAIL | Source scan previously passed; diagnostic tenant naming still exists in live data |

## B. Intelligence integrity

Paystack entity `fa8341a7-7ae9-4b23-9f78-a28dd5c9004a` produces 4,703 joined
rows and 4,703 distinct signal IDs, collapsing to 29 distinct
`(source_id, source_url, body_text_hash)` combinations. This establishes duplicate
ingestion in the observed join, rather than the same signal being repeated by it.

The TechCabal article at `/2026/08/31/paystack-acquires-allawee/` has 117
distinct signal IDs with identical URL and body hash
`sha256:3c75c7c90b9d8eefe1c850bdd3d3785967c6bb19c5df57b88f97cc06a102373b`.
One Paystack status payload has 2,323 distinct IDs for identical content.
The top ten duplicate groups were inspected; an exhaustive group inventory and
survivor/FK plan remain required. Rows consolidated: **0**.

The monitoring distribution is genuinely stored as `REGULATORY_POLICY` /
`CIRCULAR_ISSUED`. The top eight traced rows are repeated CBN circulars published
on 2019-02-28 and 2019-06-10. They have distinct signal/output/assessment IDs,
four citations each, context version 1, score 0.485, no matched decision rules,
and two matched context objects. They were rediscovered recently, which let
the former output-created-at lookback admit old publications.

The successful activation `7e468731-7d8b-4d2f-9562-21edc2a49699` scanned
11,297 outputs on September 3 using context version 1. The current profile is
version 6, with 29 active objects including ten products. No new activation was
performed in this follow-up.

Candidate fixes now:

- use publication time, with detection time only when publication is absent,
  for activation's bounded 30–60 day lookback;
- choose one existing output per source/URL/body identity for activation;
- return monitoring only for the active profile version;
- collapse duplicate company/personal monitoring to one item, preferring personal;
- count distinct current-version evidence in readiness and briefing changes;
- constrain personalisation inputs to assessments for the active profile.

Read-only execution of the actual candidate SELECTs under `sc_app_runtime`
passed in task `8aa69ad29de34aa9a3539e3697231420`: three activation candidates,
zero current-version monitoring rows, zero meaningful current-version readiness
items, and `first_value=false`. An empty corrected result is an honest
reevaluation requirement; old rows were retained as history.

## C. AI, CIL and embedding costs

Live embedding identity: OpenAI `text-embedding-3-small`, 1,536 dimensions.
All 11,297 stored embeddings fall within both observed 7/30-day windows, but
there are only 145 distinct input hashes: 11,152 redundant stored vectors.
Stored rows are **not** a provider-call or billed-token ledger, so avoided calls
and monetary savings are not claimed.

All 11,297 Global Outputs have `llm_synthesis_failed=true` despite being labelled
`synthesis_provider=openai`: 10,065 name `gpt-4.1-mini-2025-04-14`, and 1,232 name
`gpt-5-mini`. The deployed API defaults to `gpt-5-mini` and has no fallback
model/provider fields. This is failed-generation/deterministic history, not
proof of successful OpenAI synthesis. Candidate attribution repairs remain local.

Embedding probe task `f979e1133da34bc39472410aa8b45e82` made one bounded request
and received HTTP 429 / `insufficient_quota` / `credit_balance_exhausted`.
No credit purchase, recharge setting, or embedding model change was made.
The probe follows the [official embedding request contract](https://developers.openai.com/api/reference/ruby/resources/embeddings/methods/create).

CIL probe task `8b5596946fb042e4b11fb51e9335fb68` submitted a controlled
evidence question anchored to signal `1e7f87cf-34b6-45bb-bb99-130361c59be5`.
The deployed endpoint returned HTTP 500 and no correlation header. Both
provider-secret resolution attempts failed from the API task role. Independent
IAM policy simulation confirmed `implicitDeny` for `secretsmanager:GetSecretValue`
on both exact configured provider ARNs. The candidate IAM grant is still local.

CIL also now catches provider-construction/secret-resolution errors within its
deterministic fallback boundary. Regression coverage includes both generation
failure and client-construction failure.

The first candidate fallback probe in staging task
`242c956f5bf24b6d969556ec29f810b0` failed with Groq HTTP 404 for
`llama-3.3-70b-versatile`. Groq's authenticated model list excludes that model
and includes `openai/gpt-oss-120b`. Its [deprecation notice](https://console.groq.com/docs/deprecations)
confirms standard-account retirement on August 16, 2026 and recommends
`openai/gpt-oss-120b` as a replacement. The candidate default and provider
resolution tests were updated accordingly. This remains Groq-hosted generation;
the OpenAI embedding dependency is unchanged.

The replacement then passed in staging task
`cd6f967b50ef48d2a09c32086194081f`: the actual candidate fallback client received
an injected primary ReadTimeout, invoked Groq `openai/gpt-oss-120b`, and returned
the exact supplied evidence title and authorised signal citation. It reported
`provider=groq`, `fallback_used=true`, `citation_valid=true`, and
`answer_grounded=true`. No generated result was persisted as customer intelligence.
This proves the bounded candidate provider path, not the still-undeployed CIL route
or the complete fresh-tenant/provider failure matrix.

OpenAI/Groq 7/30-day token, retry, failure, and cost totals remain unavailable;
the stored vector/output counts above must not be substituted for provider billing.

## D. AWS costs and controls

Amounts below are Cost Explorer UnblendedCost in USD. End dates are exclusive.
September data is flagged `Estimated=true`; reporting may lag actual usage.
These are reported costs, not a final invoice or a statement of credits remaining.

| Window | Staging account | Payer/consolidated view |
|---|---:|---:|
| September 1–5 | $122.59 | $272.59 |
| August 29–September 5 | $224.92 | $486.74 |
| August 6–September 5 | $834.95 | $1,577.80 |
| Forecast returned for September 5–October 1 | $891.12 | $2,070.03 |

Staging's top five services over August 29–September 5:

| Service | Reported cost |
|---|---:|
| ECS/Fargate | $70.09 |
| RDS | $51.13 |
| VPC | $40.08 |
| CloudWatch | $16.03 |
| EC2 Other | $15.99 |

Material usage types include VPC endpoint hours **$36.52**, NAT gateway hours
**$15.84**, and CloudWatch metric monitoring **$14.81**. Log storage is not the
main observed CloudWatch driver. Staging 7-day regional allocation is $215.84 in
eu-west-1, $8.57 without region (tax), and approximately $0.50 global.

All costs returned blank `Environment` and `Component` billing tag groups.
Account identity establishes staging scope; tag attribution is not working in
the queried billing view and cannot be reconstructed from folder names.

The payer already has a **$100 monthly budget** with actual-spend alerts at
85%/100% and a forecast alert at 100%; all are in ALARM. It also has a default
service anomaly monitor and daily subscription with combined $100/40% impact
thresholds. Thus the earlier absence of Terraform resources did **not** mean
account controls were absent. The requested 25/50/75/90/100 alert matrix is not
fully configured. No staging-local budgets or anomaly monitors were returned.

Credits remaining, expiration, and account plan are still unverified. Obtain
the payer Billing Console credit balance/expiration and current plan before
treating credits as runway. No scaling, retention, network, or orphan deletion
was applied. Savings and a new steady-state footprint are not claimed.

## E. Workspace and verification

Canonical source remains `stem-cogent-platform`; no new clone or folder deletion.
Three reusable audit scripts were added under `backend/app/ops/` for account
inventory/costs, staging lineage, and actual candidate SQL execution. Existing
diagnostic launchers were inspected before their bounded provider checks.

The pre-existing dirty worktree was preserved. Historical screenshots, state,
and diagnostic folders were retained. Additional ignored state/plan artifacts
were noticed inside the canonical staging Terraform directory; they were not
opened or deleted.

Ruff passed. Focused generation, acceptance, product API, and CIL regressions:
**43 passed**, with only the existing Starlette deprecation warnings. Four
candidate SELECTs passed in staging's read-only runtime-role session. The
previous frontend build/responsive evidence remains applicable to unchanged
frontend source. No commit or application deployment was made.

## F. Fresh-tenant transcript

Not started. The current diagnostic tenant was used only for investigation and
candidate read-only query validation. It is not fresh-tenant acceptance proof.

## G. Verdict and concrete remaining blockers

**NOT READY — BLOCKERS REMAIN**

1. OpenAI embeddings currently return `credit_balance_exhausted`; clustering is
   deliberately paused. CloudTrail confirms a manual pause on September 3,
   preserved by the September 4 deployment.
2. At queue sampling, scored work had 42,764 pending messages and 151,016 DLQ
   messages. Ingestion priority/standard DLQs had 867/522; synthesized DLQ had 5.
   These require a bounded recovery plan after provider and dedup repairs.
3. The deployed API cannot read either generation-provider secret; CIL returns 500.
4. Existing evidence is massively duplicated and monitoring uses stale context.
   Backup-backed historical consolidation and current-context activation remain.
5. Candidate changes, IAM correction, and migration 0028 are not deployed.
6. Fresh-tenant onboarding, continuous intelligence, alerts/digests, and full
   cross-tenant mutation/RLS acceptance remain unproven.
