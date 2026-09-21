# STEM COGENT — DOCUMENT 11: PHASE 5 — PILOT READINESS & PRODUCT EXPERIENCE HARDENING

**Document Version:** 1.0.0  
**Status:** Active Engineering Execution Specification  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-011  
**Phase:** 5  
**Target Window:** 31 August–4 September 2026  
**Owner:** Founder/Product + Engineering Lead + Frontend Lead + Backend Lead + Platform/Security Owner  
**Depends On:** SC-DOC-001 through SC-DOC-010 v2.x, SC-SEED-002 v2.x, Phase 4 production/staging implementation  
**Primary Application Domain:** `stem-cogent.com`  
**Public Marketing Domain:** `thestemgrid.com`  
**Recommended Internal Admin Domain:** `admin.stem-cogent.com`  
**Supersedes:** No existing SC-DOC. This is an additive Phase 5 execution document.  
**Core Rule:** **Do not rebuild Phase 1–4. Harden, activate, refine, and prepare the existing MVP for real guided pilots.**

---

# 0. EXECUTIVE SUMMARY

Phase 4 has produced a working Stem Cogent application with the core V2 product surfaces:

- My Decision Briefing
- Company Lens
- Watchlist & Focus Areas
- Wider Intelligence
- Alerts
- Digests
- Company Context
- Decision Lens
- Decision Brief infrastructure
- CIL / investigation capability
- authentication, tenant separation, delivery, and existing pipeline services

Phase 5 is **not a new product architecture** and is **not a restart**.

Phase 5 exists because a technically working B2B intelligence product is not yet automatically a pilot-ready enterprise product.

The primary problem to solve is:

> A qualified fintech executive must not enter Stem Cogent and see a technically correct but empty, static, generic, or development-looking workspace.

The Phase 5 outcome is:

> A qualified pilot is approved, their company is configured, real historical intelligence is activated before or immediately after first access, new intelligence continues to arrive after activation, Decision Briefs evolve as evidence changes, the user can investigate and act, and the application looks and behaves like a premium modern B2B intelligence product.

Phase 5 introduces four major capabilities without changing the fundamental architecture:

1. **Guided Pilot Provisioning**
2. **First Value Activation + Continuous Intelligence**
3. **Decision Paths / Response Guidance**
4. **Premium UX/UI + Responsive Product Hardening**

The guiding product model remains:

```text
Company Context
      ×
Decision Lens
      ×
Focus Areas
      ×
Verified Live Signals
      ↓
Decision Relevance
      ↓
Decision Brief
      ↓
Human Decision
```

Phase 5 extends the last part:

```text
Decision Brief
      ↓
Decision Paths
- gaps / constraints
- plausible response options
- next things to validate
- remaining uncertainty
      ↓
Human Decision
```

Stem Cogent does **not** become an autonomous strategy, compliance, operations, or remediation engine.

The human remains the decision owner.

---

# 1. PHASE 5 GOAL

## 1.1 Primary Goal

Convert the existing Phase 4 implementation into a **credible, alive, secure, guided, pilot-ready B2B product** that can be put in front of fintech founders, CEOs, CSOs, COOs, CFOs, Product leaders, and adjacent ICP users without the team needing to explain away empty screens or technical implementation states.

## 1.2 What Phase 5 Must Prove

At the end of Phase 5, the team must be able to invite a real pilot and demonstrate this flow:

```text
Qualified pilot
   ↓
Tenant approved/provisioned
   ↓
Company Context configured
   ↓
Configured competitors/dependencies/products resolve to canonical entities
   ↓
Historical First Value Activation runs
   ↓
Real company-relevant intelligence exists
   ↓
User receives invitation
   ↓
User configures Decision Lens + Focus Areas
   ↓
Personal briefing is generated
   ↓
User sees relevant Decision Briefs / Relevant Monitoring
   ↓
New external signals continue to arrive after first login
   ↓
New/updated briefs appear without rebuilding the workspace
   ↓
Alerts and Digests reflect new Decision Brief activity
   ↓
User investigates evidence or CIL
   ↓
User acknowledges / watches / escalates / dismisses / marks acted on
   ↓
Stem records product usage for pilot learning
```

## 1.3 Definition of “Alive”

A workspace is alive when:

- it can show real recent intelligence relevant to configured context;
- it continues to process fresh data after activation;
- new information is visibly distinguishable from previously seen information;
- Decision Briefs can change when the underlying evidence materially changes;
- the user can see that Stem is actively monitoring;
- the user can investigate beyond the ranked briefing;
- the user does not need to manually search to receive value;
- search/CIL remains available when the user wants to pull intelligence;
- no customer-facing surface exposes internal implementation terminology.

---

# 2. NON-NEGOTIABLE PHASE 5 CONSTRAINTS

## 2.1 No Rebuild

Engineering must preserve all working Phase 1–4 infrastructure and application logic unless a concrete defect requires correction.

Do **not**:

- recreate the database from scratch;
- replace PostgreSQL;
- replace SQS;
- replace the existing auth model;
- replace the existing signal pipeline;
- replace the existing Decision Relevance model;
- redesign the taxonomy again;
- introduce a new frontend framework;
- rewrite the backend in another language;
- introduce advanced ML training;
- introduce Neo4j;
- introduce ClickHouse;
- introduce SageMaker;
- build mobile native apps;
- build a full integration marketplace;
- build Slack/Teams/Salesforce integrations this week;
- build autonomous remediation.

Phase 5 should be implemented through:

- additive migrations;
- existing service extension;
- new internal/admin interfaces;
- new orchestration jobs;
- frontend component redesign;
- better loading/empty/error states;
- live-update wiring;
- bounded Decision Paths;
- pilot analytics;
- security hardening.

## 2.2 No Fake Pilot Intelligence

Production pilot workspaces must not be populated with fabricated “demo” Decision Briefs.

Permitted:

- real historical Global Intelligence processed against the pilot's real Company Context;
- real current signals;
- staging-only fixtures used for automated QA;
- explicitly labelled demo fixtures in non-production environments.

Not permitted:

- invented CBN circulars;
- fake competitor changes;
- fake outages;
- fake revenue exposure;
- hardcoded Decision Briefs presented as genuine intelligence.

## 2.3 No Unsupported Monetary Claims

If Stem does not have authorised customer financial data, do not state exact revenue loss, margin loss, or transaction-value exposure.

Use:

> `Financial exposure not quantified — authorised internal financial data is not connected.`

## 2.4 No Autonomous Final Recommendation

Decision Paths may surface plausible options and what should be validated.

They must not impersonate the executive decision-maker.

Preferred language:

- “Options to consider”
- “Possible response paths”
- “Before deciding, validate…”
- “Stem does not currently know…”
- “This decision remains human-owned”

Avoid:

- “You should definitely…”
- “The correct decision is…”
- “Immediately do X” unless X is a deterministic platform safety instruction rather than a business decision.

---

# 3. CANONICAL PHASE 5 PRODUCT VOCABULARY

Use these terms exactly.

| Term | Meaning |
|---|---|
| **Pilot** | A qualified 21-day guided evaluation of Stem Cogent with a real fintech/company context. |
| **Pilot Provisioning** | Approval, tenant setup, Company Context preparation, invitation, and activation sequence before/around first login. |
| **First Value Activation** | Processing real recent historical Global Intelligence against a pilot's configured Company Context so the workspace does not begin empty. |
| **Continuous Intelligence** | Ongoing processing of new Signals/Global Intelligence after First Value Activation. |
| **Relevant Monitoring** | Company/user-relevant intelligence that does not currently cross the Decision Brief threshold. |
| **Since Your Last Visit** | Material new/updated intelligence since the user's previous briefing view. |
| **Decision Paths** | Bounded response guidance attached to a Decision Brief: gaps/constraints, plausible options, next validation steps, and remaining unknowns. |
| **Pilot Admin Console** | Internal Stem-only interface used to provision tenants, resolve entities, run activation, inspect briefs, and review pilot usage. |
| **Brief Material Change** | A change in evidence, confidence, status, urgency, applicability, decision window, exposure, or other field significant enough to be shown as an update. |
| **Product Event** | Privacy-aware usage telemetry generated by meaningful product interactions. |

Do not create alternate public labels such as “AI Playbook”, “Auto Decision”, “Fix Engine”, or “Remediation Bot” in Phase 5.

---

# 4. DOMAIN & ROUTING MODEL

## 4.1 Public Marketing

```text
https://thestemgrid.com
```

Purpose:

- marketing;
- product explanation;
- pricing;
- pilot request;
- public content.

The marketing site must not host the authenticated workspace.

## 4.2 Authenticated Application

```text
https://stem-cogent.com
```

Purpose:

- login;
- authenticated user workspace;
- onboarding;
- briefing;
- Company Lens;
- Watchlist;
- Wider Intelligence;
- Alerts;
- Digests;
- CIL;
- settings.

Recommended behavior:

```text
GET /
if authenticated:
    redirect /briefing
else:
    redirect to /login
```

The product is gated by authentication and authorisation, not by hiding its existence.

## 4.3 Internal Admin

Recommended:

```text
https://admin.stem-cogent.com
```

Alternative if deployment time is constrained:

```text
https://stem-cogent.com/internal/admin
```

The internal route must require Stem administrative permission and must not be reachable by normal tenant Admin users merely because they are admins within their fintech.

Create a separate internal permission:

```text
SYSTEM_ADMIN
```

This is distinct from tenant `ADMIN`.

---

# 5. PHASE 5 MASTER EXECUTION SEQUENCE

```text
STAGE 5.0  Phase 4 Baseline & Release Safety
STAGE 5.1  Guided Pilot Access & Provisioning
STAGE 5.2  Context Activation & Entity Resolution
STAGE 5.3  First Value Activation
STAGE 5.4  Continuous Intelligence & Brief Lifecycle
STAGE 5.5  Decision Paths / Response Guidance
STAGE 5.6  Premium UX/UI & Responsive Hardening
STAGE 5.7  Pilot Analytics & Internal Admin Visibility
STAGE 5.8  Security & Pilot Operational Hardening
STAGE 5.9  End-to-End QA, Pilot Dry Run & Release
```

Priority:

- **P0:** must ship this week.
- **P1:** required for pilot-quality experience; ship unless a P0 issue blocks release.
- **P2:** stretch only; do not delay Phase 5 release.

---

# 6. STAGE 5.0 — PHASE 4 BASELINE & RELEASE SAFETY

**Priority:** P0  
**Purpose:** Prevent Phase 5 from destabilising a working Phase 4 product.

## TASK 5.0.1 — Create Phase 4 Release Tag

Create a git tag / protected reference before Phase 5 changes.

Suggested:

```text
phase4-complete-2026-08-31
```

Done when:

- backend commit is identified;
- frontend commit is identified;
- infrastructure commit is identified;
- database migration head is recorded;
- staging build is reproducible.

## TASK 5.0.2 — Capture Baseline Smoke Tests

Record current behavior for:

- login;
- onboarding;
- Company Context save/load;
- Decision Lens save/load;
- Focus Area create/update/delete;
- My Decision Briefing query;
- Company Lens query;
- Watchlist query;
- Wider Intelligence query;
- Alerts query;
- Digests query;
- CIL;
- WebSocket;
- billing/trial status;
- RLS.

No Phase 5 work begins without a reproducible baseline.

## TASK 5.0.3 — Create Feature Flags

Add Phase 5 flags:

```text
PHASE5_PILOT_INVITES_ENABLED
PHASE5_FIRST_VALUE_ACTIVATION_ENABLED
PHASE5_BRIEF_LIFECYCLE_ENABLED
PHASE5_DECISION_PATHS_ENABLED
PHASE5_NEW_UI_ENABLED
PHASE5_PRODUCT_ANALYTICS_ENABLED
```

Production default:

- off until individually verified in staging;
- enable per environment / pilot as appropriate.

## TASK 5.0.4 — Database Backup

Before additive Phase 5 migration:

- RDS snapshot;
- migration head recorded;
- rollback SQL prepared for additive columns/tables where safe.

Done when migration rollback procedure is written and tested in staging.

---

# 7. STAGE 5.1 — GUIDED PILOT ACCESS & PROVISIONING

**Priority:** P0  
**Purpose:** A pilot does not self-generate a blank workspace from a public sign-up.

## 7.1 Target Pilot Flow

```text
thestemgrid.com/pilot
       ↓
Pilot request reviewed by Stem
       ↓
Qualified
       ↓
Alignment/context call or guided setup
       ↓
Tenant provisioned
       ↓
Company Context prepared
       ↓
First Value Activation
       ↓
Invite generated
       ↓
User accepts invite
       ↓
Password/MFA setup
       ↓
Decision Lens + Focus Areas
       ↓
Personal briefing
```

Phase 5 does not require building a CRM.

The public pilot form may continue using the existing marketing implementation.

The application must support the workflow **from approved pilot onward**.

## TASK 5.1.1 — Add Tenant Invitation Table

**Additive Migration:** `0011_phase5_pilot_invites_and_activation`

Create:

```sql
CREATE TABLE auth.tenant_invitations (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    email            CITEXT NOT NULL,
    permission_role  VARCHAR(30) NOT NULL,
    invited_by       UUID REFERENCES auth.users(id),
    token_hash       TEXT NOT NULL UNIQUE,
    status           VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                     -- PENDING | ACCEPTED | EXPIRED | REVOKED
    expires_at       TIMESTAMPTZ NOT NULL,
    accepted_at      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Rules:

- store only token hash;
- raw token appears only in generated invitation URL;
- one-time use;
- default expiry 48 hours;
- resending revokes prior pending token for same email/tenant;
- audit all invite create/revoke/accept events.

## TASK 5.1.2 — Admin Tenant Provisioning Endpoint

Create/extend:

```text
POST /internal/admin/tenants
GET  /internal/admin/tenants
GET  /internal/admin/tenants/{tenant_id}
PATCH /internal/admin/tenants/{tenant_id}
```

Minimum provisioning fields:

- canonical company name;
- company website/domain;
- business model/category;
- market(s);
- pilot start date;
- pilot status;
- plan = TRIAL;
- pilot owner inside Stem;
- internal notes (never tenant-visible).

Do not automatically start the 21-day timer on tenant row creation.

## TASK 5.1.3 — Trial Start Rule

Canonical Phase 5 rule:

> The 21-day guided pilot starts when the first invited user completes initial personal setup and First Value Activation is available, not when a lead fills a form and not when an internal tenant row is created.

Persist:

```text
trial_started_at
trial_ends_at = trial_started_at + 21 days
```

Admin may override only with explicit audit event.

## TASK 5.1.4 — Invitation API

Create:

```text
POST /internal/admin/tenants/{tenant_id}/invitations
POST /internal/admin/invitations/{invitation_id}/revoke
POST /auth/invitations/accept
GET  /auth/invitations/validate?token=...
```

Acceptance:

- invalid token returns generic failure;
- expired token cannot be replayed;
- accepted token cannot be replayed;
- wrong tenant cannot be supplied by client;
- user is created/attached server-side.

## TASK 5.1.5 — Invite-Only Registration UX

Routes:

```text
/login
/invite/accept?token=...
```

Do not expose unrestricted `/register`.

Unauthenticated user who visits `/briefing`:

- redirect `/login`.

User with no account who visits root:

- redirect `/login`.

Public marketing remains at `thestemgrid.com`.

## TASK 5.1.6 — Pilot Setup Checklist in Admin

For each tenant display:

```text
[ ] Tenant created
[ ] Company profile complete
[ ] Products configured
[ ] Markets configured
[ ] Dependencies configured
[ ] Competitors configured
[ ] Strategic priorities configured
[ ] Entities resolved
[ ] Historical activation complete
[ ] At least one relevant monitoring result OR qualifying Decision Brief exists
[ ] Invitation issued
[ ] User accepted
[ ] Decision Lens complete
[ ] Focus Areas complete
[ ] Personal ranking run
[ ] Pilot active
```

The system must make incomplete setup visible internally.

---

# 8. STAGE 5.2 — CONTEXT ACTIVATION & ENTITY RESOLUTION

**Priority:** P0  
**Purpose:** Company Context cannot work if configured objects remain unresolved strings.

## 8.1 Required Product Behavior

The customer must never see:

> `Entity link needed`

as normal customer-facing copy.

If the Company Context contains:

- Flutterwave;
- Moniepoint;
- OPay;
- Paystack;
- Kuda;
- NIBSS;
- Interswitch;
- Providus Bank;
- CBN;

the platform should resolve those values against the canonical entity registry.

## TASK 5.2.1 — Entity Resolution Audit

For every Company Context object with a known entity-bearing type:

- competitor;
- dependency;
- regulator;
- partner;
- market where represented by canonical geography;
- company watchlist item;

run entity resolution.

Output:

```text
RESOLVED
AMBIGUOUS
UNRESOLVED
NOT_APPLICABLE
```

Do not apply entity linking to pure free-text priorities such as:

> “Improve merchant profitability”

unless there is an explicit entity reference.

## TASK 5.2.2 — Automatic Exact/Alias Matching

Resolution order:

1. exact canonical name;
2. exact alias;
3. normalised exact name;
4. high-confidence deterministic alias match;
5. existing entity-resolution service;
6. internal review queue.

Do not use an unconstrained LLM to silently create entities.

## TASK 5.2.3 — Internal Entity Review Queue

Build UI over existing entity-curation/admin capabilities.

Admin screen:

```text
Unresolved Context Objects
----------------------------------------------------
Tenant       Value             Type        Suggested
Stem Test    MainOne DC        DEPENDENCY  MainOne
...
[Link] [Create] [Dismiss]
```

A linked object becomes immediately usable by Company Context relevance evaluation.

## TASK 5.2.4 — Customer-Facing Fallback Copy

If unresolved:

Do not show:

- Entity link needed
- NULL
- Failed lookup
- Resolution pending worker

Show:

> `Monitoring setup in progress`

or omit secondary linking metadata entirely.

## TASK 5.2.5 — Context Completeness Indicator

Internal/admin:

```text
Company Context completeness: 92%
Entity resolution: 14 / 15 linked
```

Customer:

Use a subtle Settings indicator only when meaningful.

Do not create gamified “profile completeness” on executive briefing.

---

# 9. STAGE 5.3 — FIRST VALUE ACTIVATION

**Priority:** P0  
**Purpose:** A qualified pilot should not experience an empty workspace merely because the system began watching after they joined.

## 9.1 Definition

First Value Activation is:

> A deterministic historical re-evaluation of existing verified Global Intelligence against a newly configured Company Context.

It uses real data.

It is not a demo.

## 9.2 Default Lookback

Configuration:

```text
PILOT_ACTIVATION_LOOKBACK_DAYS=45
```

Allowed admin range for Phase 5:

```text
30–60 days
```

Default remains 45.

Reason:

- enough recent history to demonstrate context;
- avoids overwhelming pilot;
- avoids turning onboarding into an unlimited historical-research project.

## TASK 5.3.1 — Add Activation Run Table

Add in migration `0011_phase5_pilot_invites_and_activation`:

```sql
CREATE TABLE context.activation_runs (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    initiated_by             UUID REFERENCES auth.users(id),
    lookback_days            INTEGER NOT NULL,
    context_version          INTEGER NOT NULL,
    status                   VARCHAR(20) NOT NULL,
                             -- QUEUED | RUNNING | COMPLETED | PARTIAL | FAILED
    global_outputs_scanned   INTEGER NOT NULL DEFAULT 0,
    assessments_created      INTEGER NOT NULL DEFAULT 0,
    company_briefs_created   INTEGER NOT NULL DEFAULT 0,
    relevant_monitoring_count INTEGER NOT NULL DEFAULT 0,
    started_at               TIMESTAMPTZ,
    completed_at             TIMESTAMPTZ,
    error_summary            TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

RLS:

- tenant users do not need direct access;
- internal/system admin only;
- worker service role permitted.

## TASK 5.3.2 — Historical Activation Worker

Create:

```text
backend/app/workers/tasks/pilot_activation.py
```

Inputs:

```text
tenant_id
company_context_version
lookback_days
activation_run_id
```

Algorithm:

```text
1. Load active Company Context.
2. Verify minimum required context exists.
3. Query Global Intelligence Outputs created/published within lookback.
4. For each output:
   a. evaluate tenant relevance;
   b. persist idempotent decision.assessments;
   c. if material threshold reached, create/update company-level Decision Brief;
   d. otherwise record as Relevant Monitoring where relevance threshold is met.
5. Recompute tenant summary.
6. Store activation counters.
7. Publish ACTIVATION_COMPLETED event.
```

Idempotency:

Running twice with same:

```text
tenant_id + global_output_id + context_version
```

must not create duplicates.

## TASK 5.3.3 — Activation API

Create:

```text
POST /internal/admin/tenants/{tenant_id}/activation
GET  /internal/admin/tenants/{tenant_id}/activation
GET  /internal/admin/activation/{run_id}
```

Admin UI displays progress.

## TASK 5.3.4 — Personalisation After User Setup

Company-level activation can occur before user invitation.

After user accepts invitation and completes Decision Lens:

```text
1. Load existing company assessments/briefs.
2. Evaluate Decision Lens + Focus Areas.
3. Create/update user-personalised Decision Briefs.
4. Compute personal Relevant Monitoring.
5. Set briefing ready.
```

This step should complete quickly because global/tenant work is already done.

Target:

```text
P95 < 60 seconds for initial user personalisation over activated tenant scope.
```

If longer, show progress screen rather than blank briefing.

## TASK 5.3.5 — First Value Readiness Gate

Admin must not mark tenant **READY TO INVITE** unless one of these is true:

**A.**
At least one company-level Decision Brief exists.

**OR B.**
At least three meaningful Relevant Monitoring items exist.

**OR C.**
No relevant recent intelligence exists and Stem explicitly decides the pilot may proceed because the configured scope is intentionally narrow.

Option C requires internal note; do not fabricate content.

## TASK 5.3.6 — Activation Empty State

If activation returns no Decision Briefs:

Customer copy:

> **Nothing currently requires action.**  
> Stem is monitoring your configured company context and will surface a Decision Brief when a development crosses the materiality threshold.

If Relevant Monitoring exists:

> **Nothing currently requires action.**  
> Stem is monitoring **{N} relevant developments** for your configured context.

Button:

`Review relevant monitoring`

---

# 10. STAGE 5.4 — CONTINUOUS INTELLIGENCE & BRIEF LIFECYCLE

**Priority:** P0  
**Purpose:** First Value Activation is only the initial state. Stem must keep working afterward.

## 10.1 Continuous Intelligence Rule

Every new Global Intelligence Output generated after pilot activation must automatically enter tenant relevance evaluation for active pilot/paid tenants.

The user must not need to search first.

Pipeline:

```text
New Signal
  ↓
Validation
  ↓
Classification / enrichment
  ↓
Global Intelligence Output
  ↓
Active tenant relevance fan-out
  ↓
Decision Relevance Assessment
  ↓
Company Decision Brief / Relevant Monitoring
  ↓
Decision Lens ranking
  ↓
My Decision Briefing
  ↓
Alert / Digest / WebSocket
```

## TASK 5.4.1 — Verify/Repair Tenant Relevance Fan-Out

Existing Decision Brief worker must be verified to process new Global Intelligence continuously.

Acceptance:

- create one staging Global Intelligence Output;
- matching tenant receives new assessment;
- non-matching tenant does not receive a personal claim;
- user briefing updates.

If the current worker only produces briefs in batch/on request, add event-driven fan-out.

## TASK 5.4.2 — Brief Lifecycle Fields

Additive migration `0012_phase5_brief_lifecycle_and_paths`:

```sql
ALTER TABLE decision.briefs
ADD COLUMN first_published_at TIMESTAMPTZ,
ADD COLUMN last_material_change_at TIMESTAMPTZ,
ADD COLUMN resolved_at TIMESTAMPTZ,
ADD COLUMN material_change_count INTEGER NOT NULL DEFAULT 0;
```

Keep current `brief_status`.

Canonical status values:

```text
OPEN
WATCHING
ESCALATED
ACTED_ON
DISMISSED
EXPIRED
RESOLVED
```

Do not create a complicated workflow engine.

## TASK 5.4.3 — Brief Material Change Detection

A material change includes:

- new evidence source materially changes certainty;
- confidence band changes;
- active incident status changes;
- regulation deadline changes;
- decision window changes;
- Company Context match changes;
- decision_required changes;
- material exposure/stakes change;
- underlying event becomes resolved/withdrawn;
- user/company action changes status.

When material:

```text
last_material_change_at = now()
material_change_count += 1
updated_at = now()
```

Emit:

```text
BRIEF_UPDATED
```

## TASK 5.4.4 — Brief Update History

For this week, do not build a full revision document database unless needed.

Use:

- existing audit events;
- `updated_at`;
- `material_change_count`;
- source/evidence timestamps.

On Decision Brief detail, show a compact timeline:

```text
08:47  Stem detected initial development
09:12  Second evidence source added
09:20  Confidence moved Moderate → High
11:05  Source reported issue resolved
```

If audit events cannot efficiently support this, create a small additive table:

```sql
decision.brief_events
(id, tenant_id, brief_id, event_type, event_metadata, created_at)
```

This table is optional P1, not P0.

## TASK 5.4.5 — Since Your Last Visit

Create endpoint:

```text
GET /briefing/changes?since={ISO8601}
```

Return:

```json
{
  "new_briefs": 2,
  "updated_briefs": 1,
  "new_evidence_items": 3,
  "new_relevant_monitoring": 4,
  "critical_count": 0,
  "since": "..."
}
```

Source of `since`:

- client may provide last stored session timestamp;
- server should maintain a safe per-user last briefing view timestamp via product-event telemetry or user preference metadata.

Customer-facing section:

```text
Since your last visit
2 new relevant developments
1 Decision Brief updated
3 new evidence items
```

## TASK 5.4.6 — Decision WebSocket Events

Existing live-update infrastructure must support:

```text
BRIEF_CREATED
BRIEF_UPDATED
ALERT_CREATED
RELEVANT_MONITORING_ADDED
DIGEST_AVAILABLE
```

Frontend behavior:

- do not reorder content while user is reading;
- show non-blocking banner/toast;
- allow user to click `Review updates`;
- refresh query cache after user accepts.

Example:

> **1 new Decision Brief is available**  
> `Review`

## TASK 5.4.7 — Freshness Metadata

Decision Brief/detail should display:

- published time where known;
- detected time;
- last verified time;
- last material update.

Preferred compact copy:

> Detected 38 min ago · Last verified 8 min ago

Avoid exposing scheduler/queue details.

---

# 11. STAGE 5.5 — DECISION PATHS / RESPONSE GUIDANCE

**Priority:** P1  
**Purpose:** Extend Decision Brief value without turning Stem into autonomous remediation.

## 11.1 Product Principle

Existing Decision Brief answers:

- What changed?
- Why does it matter?
- What is affected?
- What is at stake?
- What decision exists?
- What evidence supports it?

Decision Paths adds:

- What gap/constraint is preventing a straightforward decision?
- What plausible response paths exist?
- What should be validated before choosing?
- What remains unknown?

## 11.2 Customer-Facing Name

Use:

# **Decision Paths**

Sub-sections:

- **Gaps & constraints**
- **Options to consider**
- **What to validate next**
- **Remaining unknowns**

Do not label it:

- “How to fix it”
- “AI recommendation”
- “Best decision”
- “Auto-remediation”

## TASK 5.5.1 — Add Decision Path Fields

Migration `0012_phase5_brief_lifecycle_and_paths`:

```sql
ALTER TABLE decision.briefs
ADD COLUMN gaps_summary TEXT,
ADD COLUMN response_options JSONB,
ADD COLUMN next_validation_steps TEXT[],
ADD COLUMN guidance_status VARCHAR(20) NOT NULL DEFAULT 'NOT_GENERATED',
ADD COLUMN guidance_generated_at TIMESTAMPTZ,
ADD COLUMN guidance_rule_version VARCHAR(30);
```

`uncertainties` remains the canonical remaining-unknowns field.

`response_options` shape:

```json
[
  {
    "option_code": "MONITOR",
    "title": "Continue monitoring",
    "description": "Maintain current configuration while watching...",
    "tradeoffs": ["..."],
    "evidence_signal_ids": ["uuid"]
  }
]
```

## TASK 5.5.2 — Decision-Path Template Registry

Do not allow the LLM to invent unconstrained response strategies.

Use existing `config.decision_rules.output_contract` to optionally include:

```json
{
  "response_path_templates": [
    "MONITOR",
    "ESCALATE",
    "REROUTE",
    "COMMUNICATE"
  ],
  "required_validation": [
    "ALTERNATIVE_ROUTE_COST",
    "CURRENT_FAILURE_RATE"
  ]
}
```

Initial Decision Types that must support Decision Paths this week:

1. `REGULATORY_IMPLEMENTATION`
2. `REROUTE_OR_FAILOVER`
3. `PRICING_RESPONSE`

Stretch:

4. `MARKET_ENTRY`
5. `RISK_CONTROL_CHANGE`

## TASK 5.5.3 — Bounded Guidance Generator

Create:

```text
backend/app/intelligence/decision_paths/generator.py
```

Input:

- Decision Brief;
- deterministic Decision Relevance Assessment;
- matched Company Context objects;
- allowed path templates from decision rule;
- evidence package;
- uncertainties.

Process:

```text
1. Select allowed templates deterministically.
2. Remove options whose required context is known to be impossible.
3. Assemble evidence-grounded context.
4. Use bounded LLM only to:
   - phrase gaps clearly;
   - phrase selected options;
   - explain known trade-offs supported by context/evidence;
   - phrase validation questions.
5. Citation verification.
6. Store guidance.
```

LLM prohibited from:

- creating new factual claims;
- inventing company capabilities;
- inventing financial amounts;
- inventing legal obligations;
- assigning a final “best” option;
- suppressing uncertainty.

## TASK 5.5.4 — Fallback When Context Is Insufficient

If safe options cannot be generated:

Show:

> **What to validate next**

Example:

- Confirm whether alternative rail is available.
- Confirm current transaction failure rate.
- Confirm affected customer segment.
- Confirm regulatory implementation deadline.

It is better to show useful gaps than speculative advice.

## TASK 5.5.5 — Decision Paths UX

Inside Decision Brief detail:

```text
DECISION PATHS

Gaps & constraints
...

Options to consider
A. ...
B. ...
C. ...

What to validate next
[ ] ...
[ ] ...

Remaining unknowns
...
```

Add trust copy:

> Stem surfaces evidence-grounded paths for consideration. The decision remains human-owned.

Decision Paths must not dominate the brief above evidence and decision context.

---

# 12. STAGE 5.6 — PREMIUM UX/UI & RESPONSIVE HARDENING

**Priority:** P1  
**Purpose:** Move from a clean developer implementation to a premium institutional intelligence product.

## 12.1 Visual Direction

Canonical design character:

> **Institutional intelligence × premium strategy memo × modern enterprise software**

Do not use:

- cyberpunk;
- dark neon;
- glowing AI gradients;
- glassmorphism everywhere;
- decorative charts;
- “AI magic” effects;
- excessive shadows;
- oversized empty cards;
- engineering debug copy.

Use:

- light-first interface;
- warm/neutral background;
- strong near-black typography;
- restrained Stem blue accent;
- subtle semantic red/amber/green only for meaning;
- generous but purposeful whitespace;
- clear density hierarchy;
- evidence as a visible design object;
- short, confident copy;
- interactive detail on demand.

## 12.2 Design Tokens

Create central tokens rather than per-page styling.

Suggested conceptual tokens:

```text
surface.canvas
surface.primary
surface.secondary
surface.raised
border.subtle
border.strong
text.primary
text.secondary
text.muted
accent.primary
status.critical
status.high
status.standard
status.success
```

Exact final hex values remain design implementation choices, but the frontend must use semantic tokens.

Typography:

```text
Display / page title: 42–52 desktop, 32–38 tablet, 28–32 mobile
Section title: 22–28
Card title: 16–20
Body: 14–16
Metadata: 12–13
```

Minimum normal body text on desktop: 14px.

Avoid giant empty 60–80px headings if they reduce information density.

## 12.3 Layout Grid

Desktop:

```text
sidebar: 232–248px
content: max-width 1440px
content gutter: 28–36px
12-column responsive grid
right context rail: 280–340px where needed
```

Sidebar:

- collapsible;
- active state;
- notification counts only when meaningful;
- no visual clutter.

Topbar:

- contextual global search;
- alerts;
- company identity;
- account menu.

## TASK 5.6.1 — Redesign Application Shell

Files likely include existing:

```text
frontend/src/app/(app)/layout.tsx
frontend/src/components/shell/Sidebar.tsx
frontend/src/components/shell/TopNav.tsx
```

Required:

- premium spacing;
- collapsible sidebar;
- consistent content max-width;
- responsive navigation;
- topbar aligned with content;
- active nav state;
- notification badges;
- no page-specific shell duplication.

## TASK 5.6.2 — My Decision Briefing v2

Route:

```text
/briefing
```

Replace current KPI-heavy first impression.

Canonical page hierarchy:

```text
Good morning, {first_name}

{N} decisions require your attention
{M} relevant developments are being monitored

[Requires Your Attention]

[Since Your Last Visit]

[Relevant Monitoring]

[Focus Area Activity]

[Wider Intelligence →]
```

### Requires Your Attention

Show only material Decision Briefs.

Brief Card required fields:

- relevance/priority band;
- domain;
- what changed;
- why this matters to you;
- exposure chips;
- stakes chips;
- decision prompt;
- owner;
- decision window;
- confidence;
- evidence count;
- age;
- update marker if changed.

Actions:

- Open Brief
- Watch
- secondary menu

### Since Your Last Visit

Compact, not a huge card.

Example:

```text
SINCE YOUR LAST VISIT
2 new developments · 1 brief updated · 3 new evidence items
[Review updates]
```

### Relevant Monitoring

Rows/cards for relevant items below Decision Brief threshold.

Example:

```text
CBN consultation on ...
Monitoring · Relevant to Product / Regulatory
Updated 2h ago
```

## TASK 5.6.3 — Decision Brief Detail v2

Route:

```text
/briefs/[briefId]
```

Desktop:

```text
Main content 8 columns
Right context rail 4 columns
```

Main:

1. header;
2. what changed;
3. why it matters;
4. business exposure;
5. stakes;
6. decision required;
7. Decision Paths;
8. evidence;
9. historical / related developments.

Right rail:

- status;
- owner role(s);
- confidence;
- decision window;
- why shown to you;
- Company Context matches;
- actions.

Primary action:

`Investigate with Cogent`

Secondary:

- Acknowledge
- Watch
- Escalate
- Mark acted on
- Dismiss

## TASK 5.6.4 — Company Lens v2

Route:

```text
/company
```

Current company summary should become compact and useful.

Sections:

### Company Context Snapshot

```text
Payments fintech · Nigeria
4 products · 5 dependencies · 6 monitored competitors
```

### Strategic Priorities

Render as semantic chips/cards, not a comma-separated paragraph.

### Company Decisions Requiring Attention

Company-level Decision Briefs.

### Exposure Overview

Simple grouped list:

```text
Products
Merchant payments    3 active developments
Transfers            2
Wallet               1

Dependencies
NIBSS                 Elevated
Interswitch           Monitoring
Providus Bank         Normal
```

Do not build a complex graph.

## TASK 5.6.5 — Watchlist & Focus Areas v2

Route:

```text
/watchlist
```

Replace long dual columns.

Use tabs:

```text
Competitors
Products
Dependencies
Markets
Regulators
My Focus Areas
```

Row/card:

```text
Moniepoint
COMPETITOR
6 recent signals · 2 relevant · 1 changed today
[View]
```

Focus Area:

```text
Merchant profitability
FOCUS AREA
4 relevant developments · Updated 2h ago
[Edit]
```

Do not show “100% weight” unless user explicitly edits prioritisation and the percentage has understandable meaning.

Do not show unresolved entity engineering states.

## TASK 5.6.6 — Wider Intelligence v2

Route:

```text
/intelligence
```

Purpose:

- let users inspect the market beyond Stem's ranked briefing;
- preserve trust by allowing exploration.

Filters:

- All
- Regulatory
- Competitive/Product
- Infrastructure
- Customer/Market
- Financial/Economic
- Capital/Partnership
- Expansion
- Fraud/Risk/Trust

Additional filters:

- entity;
- confidence;
- date;
- relevant to company;
- changed recently.

Each result shows:

- event;
- source/evidence count;
- domain;
- entity;
- published/detected time;
- confidence;
- global implication;
- relevance indicator if assessment exists.

Optional link:

> `Why isn't this in my briefing?`

If implemented, explain threshold/relevance in plain language.

## TASK 5.6.7 — Alerts v2

Route:

```text
/alerts
```

Grouped:

- Today
- Earlier this week
- Older

Alert item:

- why alert fired;
- brief title;
- priority;
- time;
- status;
- read/unread.

Actions:

- Open Brief
- Mark read

Empty state:

> **No alerts right now.**  
> Stem will notify you when a Decision Brief crosses your configured delivery threshold.

Never say:

> “The alerts query completed successfully.”

## TASK 5.6.8 — Digests v2

Route:

```text
/digests
```

If no digest yet, show product intent:

```text
Your next briefing
Monday · 08:00

Will include
- Decisions requiring attention
- Unresolved watched briefs
- Important changes to Focus Areas
- Selected Wider Intelligence

[Digest settings]
```

When available:

- archive by date;
- subject/title;
- major brief count;
- unread/read state;
- open digest.

Never say:

> “query returned zero records.”

## TASK 5.6.9 — Settings v2

Tabs:

- Profile
- Decision Lens
- Focus Areas
- Company Context
- Alerts & Digests
- Team
- Billing
- Integrations (disabled/coming later if not active)

Company Context mutation remains permission-gated.

Decision Lens should be easy to understand.

Show role defaults but allow personal overrides.

## TASK 5.6.10 — Search Experience

Global search should search:

- Decision Briefs;
- Global/Wider Intelligence;
- entities;
- Focus Areas where useful.

Ranking:

1. relevant to current user;
2. relevant to company;
3. wider matching intelligence.

Do not promise generic web search unless existing CIL/live-search capability actually supports it.

## TASK 5.6.11 — Eliminate Technical Customer Copy

Globally ban customer-facing phrases such as:

- query completed successfully;
- zero records returned;
- API response;
- global output rows;
- entity link needed;
- worker;
- materialization failed;
- DB;
- SQL;
- queue;
- synthesis job;
- RLS;
- NULL.

Map internal states to user language.

Create:

```text
frontend/src/lib/product-copy/stateMessages.ts
```

Use central messages.

## TASK 5.6.12 — Loading States

Each page needs skeletons.

Do not display empty state until request is known to have returned empty.

Required sequence:

```text
LOADING → POPULATED
LOADING → EMPTY
LOADING → ERROR
```

No flash of “0” before real data loads.

## TASK 5.6.13 — Error States

Customer:

> We couldn't load this briefing. Try again.

Optional diagnostic ID:

> Reference: SC-7F3A

Internal logs contain actual error.

Do not display stack traces or API detail.

## TASK 5.6.14 — Responsive Behavior

Required widths:

```text
1440 desktop
1280 desktop/laptop
1024 tablet landscape / small laptop
768 tablet
390 mobile
```

Desktop:

- fixed/collapsible sidebar.

Tablet:

- compact sidebar or drawer.

Mobile:

- drawer/bottom navigation;
- stacked Brief cards;
- right rail moves below content or into tabs;
- no horizontal table overflow;
- filters become chips/dropdowns;
- CIL becomes full-screen sheet.

Phase 5 must not ship desktop-only layout overflow.

## TASK 5.6.15 — Interaction / Motion

Use motion only to clarify state.

Allowed:

- subtle page/card entrance;
- drawer/sheet transition;
- new-brief toast;
- accordion/evidence expand;
- hover/focus affordance;
- status change confirmation.

Avoid:

- decorative parallax;
- glowing animation;
- excessive spring effects;
- constant animated backgrounds.

Respect:

```text
prefers-reduced-motion
```

## TASK 5.6.16 — Accessibility

Minimum:

- WCAG 2.1 AA contrast;
- keyboard access;
- visible focus;
- semantic headings;
- form labels;
- status not conveyed by colour alone;
- icons include accessible label where interactive;
- screen reader live region for new-brief notices;
- modal/drawer focus trap.

---

# 13. STAGE 5.7 — PILOT ANALYTICS & INTERNAL ADMIN VISIBILITY

**Priority:** P1  
**Purpose:** Replace “did you like it?” with observed pilot behavior.

## TASK 5.7.1 — Product Events Table

Add to migration `0013_phase5_product_events`:

```sql
CREATE TABLE feedback.product_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    user_id       UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    event_name    VARCHAR(80) NOT NULL,
    object_type   VARCHAR(40),
    object_id     UUID,
    metadata      JSONB NOT NULL DEFAULT '{}',
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

RLS / access:

- tenant users do not need direct raw event access;
- internal analytics role;
- data minimisation.

## 13.1 Canonical Product Events

Track:

```text
SESSION_STARTED
BRIEFING_VIEWED
BRIEF_OPENED
BRIEF_UPDATED_VIEWED
EVIDENCE_PANEL_OPENED
CIL_OPENED
CIL_QUERY_SUBMITTED
BRIEF_ACKNOWLEDGED
BRIEF_WATCHED
BRIEF_ESCALATED
BRIEF_ACTED_ON
BRIEF_DISMISSED
WIDER_INTELLIGENCE_VIEWED
WATCHLIST_ITEM_VIEWED
FOCUS_AREA_ADDED
FOCUS_AREA_UPDATED
SEARCH_PERFORMED
ALERT_OPENED
DIGEST_OPENED
DECISION_PATHS_VIEWED
```

Do not duplicate raw sensitive query text into `feedback.product_events` when CIL already has an authorised query log.

## TASK 5.7.2 — Pilot Metrics

Admin tenant dashboard should show:

```text
Pilot day: 8 / 21

Global outputs evaluated: 428
Tenant relevant: 37
Decision Briefs created: 8
Open briefs: 3

Briefs opened: 6 / 8
Evidence viewed: 5
CIL investigations: 3
Acknowledged: 4
Escalated: 1
Acted on: 1
Dismissed: 2

Active days: 6 / 8
Last active: 2h ago
```

## 13.2 Core Pilot Learning Metrics

Do not overbuild analytics.

Calculate:

### Time to First Value

```text
trial_started_at - first_useful_brief_available_at
```

Target:

- useful briefing available before or within first user session.

### Brief Open Rate

```text
opened briefs / delivered briefs
```

### Action Rate

```text
briefs with meaningful action / opened briefs
```

### Not Relevant Rate

Important signal of poor relevance.

### Evidence Engagement

Did user inspect sources?

### Investigation Rate

Did user open CIL / related evidence after a brief?

### Return Usage

- active days in first 7 days;
- day-7 return;
- weekly usage.

No vanity dashboard is required.

## TASK 5.7.3 — Pilot Admin Console

Minimum pages:

```text
/internal/admin/tenants
/internal/admin/tenants/[tenantId]
/internal/admin/entity-review
/internal/admin/pipeline
```

Tenant detail tabs:

- Overview
- Company Context
- Entity Resolution
- Activation
- Users & Invites
- Decision Briefs
- Usage
- Internal Notes

Do not expose this console to tenant Admins.

---

# 14. STAGE 5.8 — SECURITY & PILOT OPERATIONAL HARDENING

**Priority:** P0  
**Purpose:** Gated onboarding must be real security, not URL obscurity.

## TASK 5.8.1 — RLS Regression Matrix

Automated tests for:

```text
auth tenant data
context.company_profiles
context.company_objects
context.user_decision_lenses
context.focus_areas
decision.assessments
decision.briefs
decision.actions
delivery.alerts
delivery.digests
cil sessions/logs
feedback product events where applicable
private uploads
```

Required test:

```text
Tenant A authenticated user attempts direct ID access to Tenant B brief
→ 404/403
→ no data in response
→ audited if appropriate
```

## TASK 5.8.2 — Invitation Security

Verify:

- cryptographically random tokens;
- hash stored;
- HTTPS only;
- 48-hour expiry;
- one-time acceptance;
- revoke;
- rate limit;
- generic errors;
- email bound;
- tenant server-derived.

## TASK 5.8.3 — System Admin Boundary

`SYSTEM_ADMIN` must not be granted to normal tenant Admin.

Internal admin routes require:

- separate permission;
- MFA;
- audit;
- IP allowlisting optional later; do not block this week's completion if secure auth is present.

## TASK 5.8.4 — App Indexing Protection

For `stem-cogent.com` authenticated app:

```text
robots.txt:
User-agent: *
Disallow: /
```

Add:

```html
<meta name="robots" content="noindex,nofollow">
```

This is privacy/discovery reduction, not authentication.

## TASK 5.8.5 — Security Headers

Verify:

- HSTS;
- CSP;
- X-Content-Type-Options;
- Referrer-Policy;
- frame-ancestors / anti-clickjacking;
- secure cookies;
- SameSite;
- HTTPS redirect.

## TASK 5.8.6 — CORS / Domain Configuration

Allowed web application origins should explicitly include:

```text
https://stem-cogent.com
```

Admin origin if separate:

```text
https://admin.stem-cogent.com
```

Do not wildcard authenticated CORS in production.

## TASK 5.8.7 — Audit Events

Add/verify audit for:

```text
TENANT_CREATED
PILOT_ACTIVATED
INVITE_CREATED
INVITE_REVOKED
INVITE_ACCEPTED
COMPANY_CONTEXT_UPDATED
ACTIVATION_RUN_STARTED
ACTIVATION_RUN_COMPLETED
DECISION_LENS_UPDATED
FOCUS_AREA_UPDATED
BRIEF_ESCALATED
BRIEF_ACTED_ON
SYSTEM_ADMIN_LOGIN
```

---

# 15. STAGE 5.9 — END-TO-END QA, PILOT DRY RUN & RELEASE

**Priority:** P0

## TASK 5.9.1 — Create One Canonical Staging Pilot Scenario

Staging-only test tenant:

```text
Company type: Payments fintech
Market: Nigeria
User role: CEO
Products:
- Merchant payments
- Transfers
- Digital wallet

Dependencies:
- NIBSS
- Interswitch
- configured bank partner

Competitors:
- Moniepoint
- OPay
- Paystack
- Flutterwave

Strategic priorities:
- transaction success
- merchant growth
- infrastructure reliability

Focus Areas:
- merchant profitability
- CBN circulars
- NIBSS reliability
```

Use real staging-ingested or clearly identified fixture data.

## TASK 5.9.2 — Full Pilot Dry Run

Do not skip steps.

```text
1. Create tenant.
2. Configure Company Context.
3. Verify entity links.
4. Run activation.
5. Confirm company briefs/relevant monitoring.
6. Invite user.
7. Accept invite.
8. Complete Decision Lens.
9. Add Focus Areas.
10. Confirm personal briefing.
11. Inject/ingest a new staging signal.
12. Confirm relevance worker runs.
13. Confirm new/updated Brief appears.
14. Confirm WebSocket/toast.
15. Confirm alert.
16. Confirm digest inclusion.
17. Open evidence.
18. Open CIL.
19. Record action.
20. Verify product event analytics.
21. Attempt cross-tenant data access.
22. Verify denial.
```

## TASK 5.9.3 — Playwright E2E

At minimum:

- invite acceptance;
- login;
- onboarding;
- briefing;
- brief detail;
- watchlist;
- wider intelligence;
- alert;
- digest;
- action;
- admin activation;
- cross-tenant direct route denial.

## TASK 5.9.4 — Visual Regression

Capture:

```text
1440
1024
768
390
```

for:

- briefing;
- brief detail;
- company;
- watchlist;
- intelligence;
- alerts;
- digests.

Fail release for:

- clipped text;
- horizontal overflow;
- invisible action;
- overlapping navigation;
- unusable mobile modal.

## TASK 5.9.5 — Performance Gate

Targets:

```text
P95 briefing API < 1.5s under pilot load
P95 briefing visual ready < 2.5s supported baseline
P95 brief detail < 2.5s
first WebSocket reconnect < 5s after transient disconnect
activation run completes within reasonable pilot data scope
```

Do not optimise hypothetical massive enterprise scale this week.

## TASK 5.9.6 — Production Release

Release order:

```text
1. migrations
2. backend
3. workers
4. admin
5. frontend behind feature flag
6. internal smoke
7. enable new UI
8. enable pilot invites
9. enable activation
10. enable Decision Paths after verification
```

Maintain rollback to Phase 4 UI while preserving additive data.

---

# 16. PAGE-BY-PAGE CUSTOMER COPY REQUIREMENTS

## 16.1 My Decision Briefing

When populated:

> **2 decisions require your attention**  
> 7 relevant developments are being monitored.

When no action required:

> **Nothing requires action right now.**  
> Stem is monitoring 11 developments relevant to your company. 3 have changed since your last visit.

Do not say:

> No developments meet threshold.

unless in secondary technical detail.

## 16.2 Company Lens

When empty:

> **No company-level decision currently requires attention.**  
> Stem continues to evaluate new developments against your Company Context.

## 16.3 Wider Intelligence

When empty:

> **No verified intelligence is available for this view yet.**  
> Try adjusting the date or filters.

Not:

> API returned zero Global Intelligence Outputs.

## 16.4 Alerts

When empty:

> **No alerts right now.**  
> You'll be notified when a Decision Brief crosses your configured delivery threshold.

## 16.5 Digests

Before first digest:

> **Your first briefing is being prepared.**  
> Digests collect decisions requiring attention, unresolved watched briefs, Focus Area changes, and selected wider intelligence.

## 16.6 Watchlist

Unresolved internally:

Customer should not see technical state.

If necessary:

> **Monitoring setup in progress**

## 16.7 CIL

Do not use:

> Ask anything.

Use:

> **Investigate this decision**

Suggested prompts:

- Why is this relevant to my company?
- Which configured dependency caused this match?
- What evidence supports this assessment?
- What changed since the brief was created?
- What remains uncertain?

---

# 17. DECISION BRIEF 2.0 — CANONICAL CUSTOMER STRUCTURE

Every populated Decision Brief detail should follow this ordering:

```text
1. What changed
2. Why this matters to you
3. What's affected
4. What's at stake
5. Decision required
6. Decision Paths
   6.1 Gaps & constraints
   6.2 Options to consider
   6.3 What to validate next
7. What remains uncertain
8. Evidence
9. Related / historical context
10. Ownership / status / actions
```

## 17.1 Trust Metadata

Always visible:

- confidence;
- evidence count;
- source names;
- published/detected time;
- last verified;
- uncertainty.

## 17.2 Quantification Language

When supported:

> Estimated transaction exposure based on authorised tenant data: ...

When not supported:

> Financial amount not quantified — authorised internal financial data is not connected.

---

# 18. CONTINUOUS UPDATE BEHAVIOR — EXACT RULES

## 18.1 Push vs Pull

### Push

Stem continuously monitors and surfaces:

- new Decision Brief;
- material brief update;
- alert;
- digest;
- watchlist activity.

### Pull

User can:

- search;
- filter Wider Intelligence;
- open entities;
- investigate via CIL;
- review historical evidence.

Stem must support both.

## 18.2 User Does Not Need to Refresh

While logged in:

- new material update triggers WebSocket event;
- UI shows banner/toast;
- TanStack Query cache invalidated after acknowledgement;
- user chooses when to refresh current reading order.

## 18.3 Focus Area Change

When user adds/changes Focus Area:

1. update focus record;
2. invalidate personal relevance cache;
3. rerank existing relevant intelligence;
4. run limited historical re-evaluation over configured lookback;
5. show:

> `4 existing developments are newly relevant to this Focus Area.`

Do not rerun full raw ingestion.

---

# 19. ADMIN CONSOLE — EXACT MVP SCOPE

The admin console is an internal operating surface, not a separate product.

## 19.1 Tenant List

Columns:

- company;
- pilot status;
- trial day;
- context completeness;
- unresolved entities;
- activation status;
- open company briefs;
- users;
- last activity.

## 19.2 Tenant Detail

### Overview

- tenant ID;
- plan;
- pilot dates;
- internal owner;
- activation summary.

### Company Context

Edit/inspect.

### Entity Resolution

Resolve ambiguous/unresolved.

### Activation

Run / rerun with explicit reason.

### Briefs

Preview generated company briefs.

Admin may mark an obviously defective staging/pilot brief for internal review, but should not silently manipulate real customer intelligence to create artificial value.

### Users & Invites

Invite/revoke/status.

### Usage

Product events.

### Internal Notes

Never visible to customer.

## 19.3 Pipeline Health

Read-only:

- latest signal received;
- latest global output;
- Decision Brief processing lag;
- failed assessment count;
- DLQ count;
- recent worker errors.

Do not build a replacement for CloudWatch.

---

# 20. WEEK EXECUTION PLAN — FINISH BY FRIDAY 4 SEPTEMBER 2026

The team may work in parallel. P0 takes precedence.

## DAY 1 — MONDAY 31 AUGUST

### Backend / Data

- Phase 4 tag/snapshot.
- Add 0011 invitation + activation migration.
- Implement invitation service.
- Implement activation worker skeleton.
- Entity-resolution audit.

### Frontend / Design

- lock Phase 5 design tokens;
- redesign shell;
- create new Brief Card;
- create technical-copy mapping;
- prepare responsive grid.

### Platform/Security

- `stem-cogent.com` routing review;
- admin domain decision;
- robots/noindex;
- invitation security design;
- RLS regression suite setup.

### Exit Gate

- no Phase 4 regression;
- invitation data model migrated in staging;
- design system merged;
- activation worker can scan outputs in dry-run.

---

## DAY 2 — TUESDAY 1 SEPTEMBER

### Backend

- complete activation worker;
- admin activation APIs;
- personal reranking after Decision Lens;
- continuous fan-out verification;
- add lifecycle fields.

### Admin

- tenant list/detail;
- context review;
- activation controls;
- entity review.

### Frontend

- My Decision Briefing v2;
- Since Your Last Visit component;
- Relevant Monitoring;
- zero-state redesign.

### Exit Gate

- staging pilot can be activated with real historical intelligence;
- customer no longer sees entity-link/debug copy;
- briefing supports populated + no-action states.

---

## DAY 3 — WEDNESDAY 2 SEPTEMBER

### Backend/Intelligence

- Decision Paths schema;
- three required Decision Type templates;
- bounded generator;
- brief update events;
- WebSocket events.

### Frontend

- Decision Brief detail v2;
- Decision Paths;
- Company Lens;
- Watchlist tabs/cards.

### QA

- begin Playwright tests;
- start cross-tenant security tests.

### Exit Gate

- at least three Decision Path types render correctly;
- new staging signal can create/update a brief;
- browser receives live update notice.

---

## DAY 4 — THURSDAY 3 SEPTEMBER

### Frontend

- Wider Intelligence v2;
- Alerts v2;
- Digests v2;
- Settings v2;
- search refinement;
- responsive 1024/768/390;
- accessibility.

### Analytics

- product events;
- pilot metrics in admin.

### Security

- invitation replay tests;
- SYSTEM_ADMIN separation;
- headers/CORS;
- RLS complete.

### Exit Gate

- all customer pages have deliberate populated/loading/empty/error states;
- mobile has no major overflow;
- pilot analytics visible internally.

---

## DAY 5 — FRIDAY 4 SEPTEMBER

### Full Team

- canonical pilot dry run;
- Playwright;
- visual regression;
- cross-tenant test;
- performance smoke;
- production backup;
- staged production deploy;
- internal founder acceptance test.

### Release Gate

Do not invite an external pilot until all P0 release criteria pass.

---

# 21. PHASE 5 P0 / P1 / P2 SCOPE MATRIX

| Capability | Priority | This week |
|---|---|---|
| Phase 4 snapshot / rollback | P0 | YES |
| Invite-only pilot access | P0 | YES |
| Entity-resolution cleanup | P0 | YES |
| First Value Activation | P0 | YES |
| Continuous new-intelligence processing | P0 | YES |
| Live brief update notices | P0 | YES |
| RLS / tenant isolation regression | P0 | YES |
| Remove customer-facing technical copy | P0 | YES |
| Responsive critical flows | P0 | YES |
| Admin tenant/activation controls | P0 | YES |
| Decision Paths | P1 | YES, bounded |
| Premium full-page UX redesign | P1 | YES |
| Pilot product analytics | P1 | YES |
| Brief revision timeline table | P1 | ONLY IF audit events insufficient |
| Command palette | P2 | NO if time constrained |
| Slack / Teams | P2 | DEFER |
| Salesforce | P2 | DEFER |
| Advanced ML | P2 | DEFER |
| Full internal-data connectors | P2 | DEFER |
| Native mobile app | P2 | DEFER |
| Autonomous remediation | P2 | DEFER |
| Complex relationship graph | P2 | DEFER |

---

# 22. ENGINEERING ACCEPTANCE GATE

Phase 5 is complete only when all P0 boxes are checked.

## Pilot Provisioning

- [ ] Approved pilot can be provisioned without database-console manipulation.
- [ ] Invitation is token-gated, expiring, and one-time.
- [ ] 21-day pilot begins at actual activation, not request submission.
- [ ] Normal user cannot self-register an arbitrary tenant.

## Context

- [ ] Known Company Context entities resolve.
- [ ] Unresolved entities route internally.
- [ ] Customer never sees `Entity link needed`.
- [ ] Company Context remains tenant-scoped.

## First Value

- [ ] Historical activation processes real Global Intelligence.
- [ ] Activation is idempotent.
- [ ] Admin can see activation summary.
- [ ] Pilot can start with Decision Briefs or Relevant Monitoring without fake data.

## Continuous Intelligence

- [ ] New Global Intelligence evaluates against active tenants.
- [ ] New relevant brief appears automatically.
- [ ] Material change updates an existing brief where appropriate.
- [ ] WebSocket/UI notifies without page refresh.
- [ ] Alerts can reference the new/updated brief.
- [ ] Digest includes qualifying new activity.

## Decision Paths

- [ ] At least 3 required decision types have bounded path templates.
- [ ] Guidance does not fabricate facts.
- [ ] Guidance does not choose final decision.
- [ ] Missing context produces validation steps rather than hallucinated advice.

## UX/UI

- [ ] My Decision Briefing is no longer KPI-zero-first.
- [ ] Since Your Last Visit works.
- [ ] Relevant Monitoring works.
- [ ] Decision Brief detail meets canonical structure.
- [ ] Company Lens is useful.
- [ ] Watchlist is grouped and interactive.
- [ ] Wider Intelligence is explorable.
- [ ] Alerts/Digests have meaningful empty states.
- [ ] No customer-facing API/database/worker copy.
- [ ] 1440/1024/768/390 verified.
- [ ] Keyboard/focus basics pass.

## Security

- [ ] Cross-tenant direct access tests fail safely.
- [ ] System Admin is separated from tenant Admin.
- [ ] App is `noindex,nofollow`.
- [ ] CORS is explicit.
- [ ] security headers pass.
- [ ] invitation replay fails.
- [ ] audit events recorded.

## Analytics

- [ ] Brief open events recorded.
- [ ] Evidence interaction recorded.
- [ ] Decision actions recorded.
- [ ] Active days visible.
- [ ] Pilot admin can inspect usage without querying production DB manually.

## Release

- [ ] Canonical pilot dry run passes.
- [ ] No P1 production incident open.
- [ ] Phase 4 rollback path remains available.
- [ ] Production backup taken.
- [ ] Founder/Product acceptance complete.

---

# 23. PRODUCT ACCEPTANCE TEST — THE “IFE TEST”

Phase 5 should be evaluated against a simple real-world standard.

Imagine a qualified fintech executive receives access.

They should be able to say:

1. **Stem understands roughly what my company does.**
2. **Stem understands what I am responsible for.**
3. **I can immediately see something relevant rather than an empty dashboard.**
4. **I can understand why Stem thinks it matters to me.**
5. **I can inspect the evidence.**
6. **I can see what decision the development creates.**
7. **I can see plausible paths / what I need to validate next.**
8. **New information continues to arrive after my first login.**
9. **I do not have to search before Stem gives me value.**
10. **I can search/investigate when I want more.**
11. **The product feels trustworthy and professionally built.**
12. **I would know after using it whether this is worth paying for.**

If the platform cannot produce this experience, Phase 5 is not complete.

---

# 24. PILOT OPERATING PROCEDURE AFTER PHASE 5

## Before Pilot

Founder / pilot owner:

1. qualify company;
2. 15–20 minute context call;
3. provision tenant;
4. configure Company Context;
5. verify entities;
6. run activation;
7. review activation quality;
8. invite user.

## Day 1

User:

1. accept invitation;
2. configure Decision Lens;
3. choose Focus Areas;
4. enter My Decision Briefing;
5. open at least one relevant item;
6. inspect evidence.

Stem team:

- observe without interrupting;
- note failures.

## Days 2–7

Observe:

- fresh brief creation;
- brief opens;
- dismissals;
- searches;
- evidence views;
- CIL;
- alerts.

Do not over-contact.

## Day 7 Check-In

Ask:

- Which brief was most useful?
- Which was irrelevant?
- What did you do after seeing it?
- What did you expect Stem to tell you that it did not?
- Did Decision Paths help or create noise?

## Days 8–20

Continue real monitoring.

Adjust configuration only where configuration is objectively wrong.

Do not manually manufacture intelligence to improve engagement metrics.

## Day 21

Value review:

- what Stem surfaced;
- what user actually opened;
- what was acted on;
- what was dismissed;
- what was searched;
- what was missing;
- willingness to continue/pay.

---

# 25. WHAT NOT TO LEARN FROM A PILOT

Do not conclude:

> “They did not log in daily, therefore no value.”

CEO/CFO intelligence may be event-driven rather than daily.

Measure:

- whether they returned when something meaningful changed;
- whether alerts caused action;
- whether briefs influenced work;
- whether they trusted evidence;
- whether they would keep it.

Do not optimise for addictive engagement.

Stem Cogent is executive decision infrastructure, not a consumer social product.

---

# 26. FUTURE BACKLOG CREATED BY PHASE 5 — DO NOT BUILD THIS WEEK

Record only:

## Potential Post-Pilot

- Slack/Teams delivery;
- CRM/analytics/internal data connectors;
- deeper document ingestion;
- advanced Decision Path workflows;
- collaborative decision assignments;
- external partner status feeds;
- richer historical decision memory;
- automatic pilot qualification;
- custom enterprise sources;
- SSO;
- expanded Africa markets;
- advanced ML after real labelled data;
- automated ROI/value reporting where supported;
- response-path effectiveness learning.

A repeated pilot signal earns its way into the roadmap.

One person's suggestion does not automatically become architecture.

---

# 27. FINAL PHASE 5 PRINCIPLE

The team is no longer trying to prove that it can build screens.

The team is trying to prove that Stem Cogent can deliver this experience:

> **Understand my company. Understand my responsibility. Watch the outside world continuously. Tell me when something matters. Show me why. Show me the evidence. Help me understand the decision and plausible paths forward. Then let me decide.**

That is the Phase 5 release.

---

**Document End — SC-DOC-011 Phase 5: Pilot Readiness & Product Experience Hardening v1.0.0**
