# Phase 5 Live Acceptance

Status date: 2026-09-05

The expired AWS-session blocker was cleared on 2026-09-05. The sections below
retain the original repair baseline; current live findings and cost figures are
in [the September 5 live follow-up](phase5-live-followup-2026-09-05.md).
The production verdict remains **NOT READY — BLOCKERS REMAIN**, now supported
by live duplicate, provider, queue, and context-version evidence.

This ledger distinguishes repository evidence from live evidence. A result is not marked
passed until the deployed staging path and its stored data have been verified.

## Baseline

| Item | Observed |
|---|---|
| Canonical repository | `C:\Users\Alex Marco\Documents\Stem Cogent\stem-cogent-platform` |
| Canonical branch / commit | `feat/phase5-pilot-readiness` / `7eeb89f0c8431ff138a08b1b513d34f568f38ecc` |
| Current staging source line | `staging`; latest application fix `dc4755b` and acceptance-document commit `c336c03` |
| Canonical migration head before repair | `0025` |
| Staging source migration head | `0027` |
| Staging feature flags in source | All six Phase 5 flags enabled on the staging line |
| OpenAI generation configuration | `gpt-4.1-mini-2025-04-14`, bounded timeout/retries |
| Groq generation configuration | Secret is provisioned, but no fallback model/client/router exists in the canonical code |
| Embeddings | OpenAI `text-embedding-3-small`, 1,536 dimensions |
| Live AWS / DB / logs | Blocked: configured AWS session is expired and requires `aws login` |
| Existing working tree | Dirty before this repair; pre-existing documentation and tracked bytecode changes are preserved |

## Defect ledger

| ID | Symptom | Root cause | Layer | Fix | Test | Status |
|---|---|---|---|---|---|---|
| P5-LA-01 | Delivery step fails or appears to fail | One UI property combines two preferences; several mutations are non-atomic; personalisation dispatch may raise after persistence | Frontend/API/queue | Separate preferences, add durable completion, make finalisation retry-safe | API contract, frontend, refresh/relogin, queue failure | In progress |
| P5-LA-02 | Customer sees internal tenant naming | Invite correctly reads `auth.tenants.name`, but provisioning accepts internal execution names and the diagnostic tenant was named with internal terms | Admin/data/copy | Validate customer display names and repair live tenant only after authenticated DB access | Provision/invite tests; live invite | In progress |
| P5-LA-03 | Company Context is both complete and “Setup needed” | Company Lens expects `company_type` and `headquarters_country`, fields absent from the canonical profile schema | API/frontend | Return and render one canonical completeness contract | Cross-surface context test | In progress |
| P5-LA-04 | Monitoring rows have generic/blank identity | API returns `summary`; frontend expects `headline` and `relevance_reasons`, neither present in the response | API/DTO/frontend | Project supported event identity, rationale, time, and evidence fields | DTO and rendering tests | In progress |
| P5-LA-05 | Monitoring appears regulatory-only | Stored row distribution is not available without DB access; the DTO currently renders only `primary_domain`, magnifying any distribution | Data/classification/DTO | Add trace fields; inspect all live rows after login | Distribution query and activation rerun | Blocked on live access |
| P5-LA-06 | Paystack evidence repeats | Normalization checks `(raw_signal_id, body hash, URL)`, so recollection in a new job can create a new signal for identical content | Ingestion/data/API | Canonical URL/content fingerprint, cross-job idempotency, defensive distinct entity projection | Reprocessing and entity-query tests | In progress; cleanup blocked |
| P5-LA-07 | Ask Cogent returns generic failure | Canonical CIL analytics SQL passes an untyped boolean into `jsonb_build_object`; generation has no Groq fallback | API/AI routing | Bind boolean explicitly; add validated bounded fallback and graceful deterministic continuity | Provider fault matrix and CIL route tests | In progress |
| P5-LA-08 | Relationship prompt appears with no relationship data | Entity suggestions are hard-coded without checking the entity response | Frontend | Gate relationship prompts on grounded relationship availability | Component/E2E assertion | In progress |
| P5-LA-09 | Settings exposes backend implementation wording | Disabled team control includes engineering copy | Frontend copy | Replace with guided-pilot product language | Copy scan | In progress |
| P5-LA-10 | More than one “Workspace Owner” | UI relabels every tenant `ADMIN` as Workspace owner; the persisted role is tenant admin, not ownership | Auth/copy/data | Display tenant admin accurately; inspect live assignments | Role/copy/security tests | In progress |
| P5-LA-11 | Embedding retries can repeat billable calls | Existing embedding identity is checked only after calling the provider | AI cost/idempotency | Check/cache under an identity lock before provider call | Retry/concurrency tests | In progress |
| P5-LA-12 | AWS staging spend warning | No current billing evidence available; warning alone is not an invoice | AWS/FinOps | Read Cost Explorer and tagged inventory after AWS reauthentication | 7/30-day cost report | Blocked on AWS login |

## Live evidence still required

- HTTP request/response and correlation IDs for each reported path.
- Database trace for the eight Relevant Monitoring rows and Paystack duplicates.
- ECS task definitions, immutable image digests, worker revisions, and feature flags.
- OpenAI/Groq usage data and AWS Cost Explorer data for 7 and 30 days.
- A fresh-tenant staging transcript and cross-tenant security run.

## Repair disposition

| ID | Local result | Live result |
|---|---|---|
| P5-LA-01 | PASS — independent alert/digest controls and durable completion endpoint | BLOCKED — refresh/relogin not exercised against staging |
| P5-LA-02 | PASS — internal execution terms rejected and invitation heading corrected | BLOCKED — diagnostic tenant has not been renamed or replaced |
| P5-LA-03 | PASS — one canonical completeness function is used by context, Company Lens, admin, and activation | BLOCKED — deployed rows not compared |
| P5-LA-04 | PASS — monitoring DTO/UI carries title, event, entity, match, time, source, and evidence | BLOCKED — current eight rows not rerun |
| P5-LA-05 | PASS — trace fields are exposed | BLOCKED — stored distribution is inaccessible |
| P5-LA-06 | PASS — canonical fingerprint and defensive entity distinctness are implemented | BLOCKED — duplicate groups not counted or consolidated |
| P5-LA-07 | PASS — SQL binding, IAM, routing, validation, attribution, and graceful fallback repaired | BLOCKED — live primary/fallback not fault-injected |
| P5-LA-08 | PASS — relationship suggestion requires evidence-backed relationship data | BLOCKED — live entity response not retested |
| P5-LA-09 | PASS — customer engineering copy removed | PASS — static production-source scan clean; deployed scan blocked |
| P5-LA-10 | PASS — tenant ADMIN is labelled Workspace administrator | BLOCKED — live assignments not inspected |
| P5-LA-11 | PASS — embedding identity is checked under a lock before provider work | BLOCKED — usage and cache-hit counts unavailable |
| P5-LA-12 | PASS — static always-on topology inventoried | BLOCKED — AWS cost and resource APIs require reauthentication |

## AI dependency and cost-control map

| Path | Deterministic | Embedding/vector | OpenAI generation | Groq generation | Cache/idempotency |
|---|---:|---:|---:|---:|---|
| Global Synthesis | Validation fallback | Upstream canonical signal embedding/history | Primary | Eligible fallback | Completed prompt-version lock/precheck |
| Decision Paths | Yes | No additional embedding | No | No | Brief/lens/context version conflict keys |
| CIL | Retrieval and graceful answer fallback | No query embedding in current implementation | Primary | Eligible fallback | Session reuse, usage idempotency key, Redis rate limit |
| First Value Activation | Relevance and readiness rules | Reuses existing global outputs; no re-embedding | No new generation directly | No new generation directly | Activation/context version and assessment keys |
| Continuous Intelligence | Classification, scoring, relevance | One canonical signal embedding per input/model/version | Global synthesis primary | Eligible synthesis fallback | Signal, embedding, synthesis, assessment, and brief identities |
| Search | SQL `ILIKE` retrieval | No | No | No | No billable AI work |
| Entity investigation | SQL entity/evidence/relationship retrieval plus deterministic fallback | No query embedding | CIL primary | Eligible CIL fallback | CIL session/usage/rate controls |

AI usage totals for 7 and 30 days are unavailable because provider and staging access is unavailable. No monetary estimate is substituted for actual usage. The implemented controls are: 1,200 generation-output-token caps, bounded provider retries, a non-recursive single fallback, canonical embedding reuse, completed synthesis reuse, deterministic Decision Paths, and 10 CIL requests per user per minute.

## Intelligence integrity report

| Item | Result |
|---|---|
| Duplicate root cause | Cross-job ingestion identity used raw-job identity; entity projection also lacked defensive canonical distinctness |
| Duplicate groups found | Unavailable without staging DB access |
| Rows safely consolidated | 0 — destructive cleanup prohibited without group trace and backup |
| Query fan-out fixed | Locally, entity activity is distinct by fingerprint/source/URL/body identity |
| Activation rerun result | Blocked |
| Domain distribution | Blocked; no artificial diversification performed |
| Meaningful monitoring count | Blocked; readiness now requires identity, domain, event type, citations, and relevance match |

## AWS cost report

| Item | Evidence |
|---|---|
| Credits / expiry / MTD / forecast / 7-day / 30-day | Unavailable: `aws sts get-caller-identity` reports an expired session |
| Static staging topology | Two NAT gateways, one ALB, `db.t4g.large` RDS with 100–500 GiB gp3 and no replica, one `cache.t4g.medium` Redis node, 2 API + 2 frontend + 8 worker Fargate tasks |
| Log retention | API/DLQ 90 days; ingestion/processing/synthesis/delivery 30; infrastructure 14; VPC flow logs 90 |
| Existing controls | SQS receives capped at 3–5 with DLQs; ECR keeps 50 tagged releases and expires untagged layers after 7 days |
| Missing account controls in IaC | No AWS Budget thresholds or Cost Anomaly Detection resources found |
| Changes applied | None; materiality and live state cannot be established, and NAT/ALB/RDS changes require reviewed operational action |
| Recommended next inspection | Cost Explorer grouped by service, usage type, region, Environment, and Component; then evaluate idle ECS/RDS schedule and only material log/topology reductions |

## Workspace cleanup report

| Path | Type / state | Disposition |
|---|---|---|
| `stem-cogent-platform` | Canonical Git repo; active repair plus pre-existing dirty files | KEEP — sole source of truth |
| `phase5-staging-deploy` | Git repo at `c336c03`; untracked diagnostic scripts and manual acceptance evidence | KEEP TEMPORARILY — relevant runtime fixes merged; diagnostics require review |
| `stem-cogent-phase3-fix` | Clean Git repo at `345911d` | ARCHIVE/DELETE only after founder confirms no external dependency |
| `stem-cogent-phase3-release` | Clean Git repo at `0459493`; ignored local Terraform state present | SECURITY CLEANUP REQUIRED; do not delete until backend/state provenance is confirmed |
| `stem-cogent-phase4-connectivity-merge` | Git repo at `867a7da`; coverage debris and nested source folder | REVIEW then remove proven cache/nested duplicate |
| `errors` | Plain folder with ten live screenshots | REVIEW AS CUSTOMER-SENSITIVE; ledger captures symptoms, images not copied into Git |

No folder was deleted and no screenshot was committed. Potentially sensitive local Terraform state was identified by filename only and was not opened. Canonical `.gitignore` now excludes env files, logs, temp probes, coverage shards, IDE files, caches, and Terraform state.

## Fresh-tenant production gate

The required live transcript remains blocked at the first step because AWS authentication, staging database access, and provider usage access are unavailable. No existing diagnostic tenant is being substituted for fresh-tenant evidence.

`Provision → Configure Context → Resolve entities → Activate → Invite → Accept → Onboard → Briefing → Evidence → CIL → OpenAI failure/Groq fallback → Fresh intelligence → Alert/Digest → Security test`

Current verdict: **NOT READY — BLOCKERS REMAIN**.

## Final local verification

| Check | Result |
|---|---|
| Backend unit tests | PASS — 320 passed; three deprecation warnings only |
| Focused generation/CIL/provider tests | PASS — 27 passed after the final Groq configuration-continuity, credit-exhaustion, and both-provider degradation cases |
| Backend static analysis | PASS — Ruff clean across `app`, `alembic`, and `tests/unit` |
| Database migration | PASS locally — one head (`0028`) and complete offline upgrade SQL rendered |
| Frontend | PASS locally — 22/22 unit tests, ESLint, TypeScript, and Next.js production build |
| Responsive flow | PASS locally — all seven customer surfaces at 1440/1024/768/390 in the dedicated responsive rerun |
| Terraform | PASS locally — formatting, IAM 7/7, ECS 4/4 |
| Patch hygiene | PASS — `git diff --check`; only line-ending notices were emitted |

No deployment, migration apply, live data mutation, tenant rename, duplicate consolidation,
or cost-changing infrastructure action was attempted without authenticated live evidence.
