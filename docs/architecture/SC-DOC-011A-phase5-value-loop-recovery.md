# Stem Cogent — Phase 5 Value Loop Recovery & Pilot Value Acceptance
## Addendum to SC-DOC-011 — First Value, Freshness, Continuous Intelligence & Dossier Recovery

**Status:** Engineering recovery specification  
**Purpose:** Repair the gap between a technically completed onboarding flow and actual customer value.  
**Scope:** Phase 5 recovery only. This is not Phase 6 and not a rebuild.

---

# 0. Why this recovery exists

A full staging pilot flow was completed:

```text
Internal admin
→ tenant created
→ company/context configured
→ activation started
→ invitation created
→ invited user onboarded
→ onboarding completed
→ user landed in My Decision Briefing
```

The resulting user experience was not acceptable:

- `0 decisions require your attention`
- `0 relevant developments are being monitored`
- Since Your Last Visit = `0`
- Relevant Monitoring empty
- the workspace remained unchanged later in the day
- Watchlist contained configured products but no useful activity
- Wider Intelligence contained stale/old intelligence, including 2023 material
- no usable Signal Dossier/deep intelligence detail was visible from the tested flow

This is not primarily a visual-design problem.

It is a **value-loop integrity problem**.

The UI redesign must not hide this defect.

---

# 1. What counts as progress

The implementation has made real progress if the following are working:

- tenant provisioning
- invite creation/acceptance
- guided onboarding
- Company Context persistence
- Decision Lens / Focus Areas persistence
- customer route shell
- Settings
- Watchlist configuration
- Wider Intelligence storage/display
- responsive shell
- authentication / role boundaries

Those are important foundations.

However:

> **The core product promise is still not proven if a correctly onboarded fintech executive lands in an empty briefing and receives no new intelligence afterward.**

The value loop is:

```text
Company Context
× Decision Lens
× Focus Areas
× Verified Recent Intelligence
        ↓
Decision Relevance
        ↓
Decision Brief / Relevant Monitoring
        ↓
Dossier / Evidence / Cogent investigation
        ↓
Continuous updates
```

A failure anywhere in this chain can produce a technically healthy but commercially valueless workspace.

---

# 2. Source-of-truth acceptance contract

The existing Phase 5 specification already requires:

## First Value Activation

A pilot should not begin empty merely because monitoring started after invitation.

Default historical lookback:

```text
45 days
```

Allowed Phase 5 range:

```text
30–60 days
```

## Ready-to-invite gate

A tenant may be marked ready only when one of these is true:

```text
A. at least 1 company-level Decision Brief
OR
B. at least 3 meaningful Relevant Monitoring items
OR
C. explicit internal narrow-scope exception with note
```

For normal pilot acceptance, A or B is preferred.

## Personalisation after onboarding

After Decision Lens + Focus Areas complete:

```text
existing company assessments/briefs
→ personal ranking
→ personal Relevant Monitoring
→ briefing ready
```

If personalisation is still running, the user should see progress, not a blank/zero briefing.

## Continuous Intelligence

After activation:

```text
new signal
→ validation
→ classification/enrichment
→ Global Intelligence
→ active-tenant relevance fan-out
→ assessment
→ Decision Brief / Relevant Monitoring
→ personal ranking
→ briefing
→ alert/digest/WebSocket
```

The user must not have to search first.

---

# 3. P0 defect: readiness gate allowed an empty pilot

Observed outcome:

```text
0 Decision Briefs
0 Relevant Monitoring
```

after a completed pilot flow.

Unless an explicit narrow-scope exception was intentionally recorded, this violates the intended readiness gate.

## Required investigation

For the exact pilot tenant, inspect:

```text
tenant readiness state
activation_run id
activation status
lookback_days
context_version
global_outputs_scanned
assessments_created
company_briefs_created
relevant_monitoring_count
readiness gate result
readiness reason
internal exception/note if any
invitation issued_at
user onboarding_completed_at
personalisation job/result
```

Determine whether:

1. readiness gate was never enforced;
2. it used stale counters;
3. activation was marked complete incorrectly;
4. the invitation path bypassed readiness;
5. company-level activation had value but personalisation lost it;
6. personalisation never ran;
7. relevance thresholds filtered everything;
8. the current tenant legitimately had no relevant recent intelligence.

## Required fix

`READY_TO_INVITE` must be a server-side decision.

The UI may not enable/issue a normal pilot invite if the readiness contract fails.

Return an explicit internal reason:

```text
NOT_READY_NO_RECENT_INTELLIGENCE
NOT_READY_ACTIVATION_INCOMPLETE
NOT_READY_CONTEXT_INCOMPLETE
NOT_READY_ENTITY_RESOLUTION
NOT_READY_PERSONALISATION_PENDING
READY_DECISION_BRIEF
READY_RELEVANT_MONITORING
READY_NARROW_SCOPE_EXCEPTION
```

Do not expose these raw codes to customers.

---

# 4. P0 defect: historical activation freshness is not trustworthy

The user observed 2023 intelligence in a 2026 pilot experience.

Old information is not automatically wrong.

It is wrong when it is presented as current intelligence without a clearly historical role.

## Canonical freshness rule

Current First Value Activation should evaluate Global Intelligence whose **effective event/publication date** falls within the configured lookback.

Do not rely blindly on ingestion `created_at`.

Required date precedence:

```text
1. verified source published_at / event_at
2. source updated_at only when it represents a material current update
3. trustworthy extracted event date
4. fetched_at only as ingestion metadata, not proof that old content is current
```

A 2023 article fetched in 2026 must not become a 2026 current development merely because it was newly ingested.

## Historical information is still useful

Older material may appear in:

- Signal/Intelligence Dossier historical context
- related prior events
- comparison in Cogent
- evidence chronology

It must be labeled:

```text
Historical context
Originally published: 2023
```

It must not silently occupy the main current feed.

---

# 5. Add a freshness classification

Every Global Intelligence Output should have enough normalized date metadata to derive:

```text
CURRENT
RECENT
HISTORICAL
DATE_UNCERTAIN
```

Suggested semantics should follow existing product time windows rather than creating arbitrary legal truth.

For First Value:

```text
CURRENT/RECENT within activation lookback → eligible
HISTORICAL → context only
DATE_UNCERTAIN → do not count toward readiness without review
```

Do not fabricate publication dates.

---

# 6. Activation quality report

The internal activation result must show more than counters.

Add/verify an internal diagnostic summary:

```text
Activation run
Lookback: 45 days
Context version: X

Global outputs scanned          243
Eligible by freshness           118
Excluded stale/historical        97
Excluded date-uncertain          11
Excluded no-context-match        13
Relevant assessments              8
Meaningful monitoring             6
Material briefs                   1

Newest eligible development     2h ago
Oldest eligible development     41d ago
```

Also provide exclusions by reason.

This is an internal operator tool, not customer UI.

---

# 7. P0 defect: personalisation after onboarding may be dropping company value

The final user briefing contained zero value after onboarding.

Trace:

```text
company assessments before invitation
company briefs before invitation
company Relevant Monitoring before invitation
user Decision Lens
user Focus Areas
personalisation job
user-level ranking results
final briefing API
```

Questions to answer:

1. Did company-level activation have qualifying intelligence before invite?
2. Did the user's Decision Lens accidentally filter everything?
3. Did personalisation fail silently?
4. Did the UI query before personalisation completed?
5. Did personalisation use the wrong context version?
6. Is the briefing endpoint only reading user-level records that were never generated?

## Required UX behavior

If personalisation is still running:

```text
Preparing your briefing
COGI / progress state
```

Do not show zero as if zero is the final result.

Target remains the existing Phase 5 goal:

```text
P95 < 60 seconds
```

for initial personalisation over an already activated tenant.

---

# 8. P0 defect: Continuous Intelligence is not visibly alive

The platform remained unchanged later in the day.

This must be tested as a pipeline, not inferred from UI polling.

## Required live trace

Inject or allow one legitimate new staging source item after tenant activation.

Trace:

```text
source fetched
→ signal created
→ dedup
→ validated
→ classified
→ synthesized
→ Global Intelligence Output
→ tenant fan-out
→ Decision Relevance
→ company assessment
→ personal ranking
→ briefing
→ WebSocket
→ alert/digest qualification
```

Record timestamps at every step.

Calculate:

```text
signal-to-global-output latency
global-output-to-assessment latency
assessment-to-briefing latency
briefing-to-WebSocket latency
```

## Required acceptance

Matching tenant:
- receives assessment
- receives Relevant Monitoring or Decision Brief when thresholds qualify
- briefing changes without reactivation

Non-matching tenant:
- receives no personalized claim

Logged-in browser:
- receives live update or visible freshness change without manual rebuild/re-onboarding

---

# 9. Pipeline heartbeat / staleness guardrail

The operator should be able to know whether Stem is actually monitoring.

Add/verify internal metrics:

```text
last successful source collection
last validated signal
last Global Intelligence Output
last tenant fan-out
last successful personal ranking
oldest unprocessed queue item
DLQ count
newest customer-visible intelligence age
```

Raise internal warning if an expected live source pipeline becomes stale.

Do not display technical queue terminology to customers.

---

# 10. P0/P1 defect: Wider Intelligence is a corpus, not yet a trustworthy current intelligence surface

The tested Wider Intelligence screen appears to be a long undifferentiated feed and included stale content.

Default behavior must make current, useful intelligence obvious.

## Required default

Default filter/sort should emphasize:
- current/recent
- verified
- priority/relevance where applicable

Do not allow old records to dominate because they were re-ingested recently.

## Historical mode

Offer deliberate history via:
- date filter
- historical context
- dossier related history

Do not erase valuable historical evidence.

---

# 11. Signal Dossier / Intelligence Dossier recovery

Earlier product specifications require a deep detail view for a signal/intelligence item.

The tested experience did not make this capability visible/useful.

This is a product-value surface, not optional decoration.

## Purpose

Every intelligence item should allow the user to go from:

```text
headline / monitoring row
→ full intelligence detail
→ evidence
→ historical context
→ affected entities
→ Cogent investigation
```

## Minimum dossier contract

When supported by stored data:

```text
title
domain
event type
published/event date
current vs historical label
executive summary / what changed
why this matters
confidence
evidence sources
affected entities
related intelligence
historical context
tenant relevance explanation when applicable
Open in Cogent / Investigate
```

Do not invent a recommendation.

For tenant-specific value, the dossier should separate:

```text
GLOBAL FACT
what happened in the market

TENANT INTERPRETATION
why Stem thinks it matters to this company/user
```

## Routing

Inspect the existing route before creating a new one.

Reuse the existing Signal Dossier/detail route if it exists.

If V2 renamed the underlying model, preserve compatibility/redirect rather than duplicating two detail systems.

---

# 12. Watchlist is currently configuration, not intelligence

Observed Watchlist product rows include values such as:

```text
and Invoicing
Invoicing
Online payments
Recurring payments
```

and repeated copy:

```text
Monitoring will begin when this context is matched
```

Problems:

1. `and Invoicing` suggests an onboarding/context parsing normalization bug.
2. Product rows do not show whether monitoring has actually matched anything.
3. Every row has the same passive state.
4. There is no latest relevant development/activity signal.

## Required repair

Normalize configured product strings.

Trace where `and Invoicing` came from:
- onboarding parser
- seed
- admin context creation
- comma/list parsing
- model output

Do not simply edit this one tenant's row.

## Watchlist useful state

When no match:

```text
Monitoring
No verified developments matched in the last 30 days
```

When active:

```text
3 relevant developments
1 new today
Latest: ...
```

Use real counts only.

Watchlist remains scope/control; it should also prove that monitoring is active.

---

# 13. First-use landing contract

A qualified pilot's first successful login/onboarding completion must resolve to one of three deliberate states.

## State A — Material value

```text
1+ Decision Brief
+
Relevant Monitoring
```

## State B — Monitoring value

```text
0 Decision Briefs
3+ meaningful Relevant Monitoring
```

## State C — genuinely no recent match

This should normally prevent normal readiness/invite.

If an approved narrow-scope exception exists, the customer experience must not look broken.

Show:

```text
Stem is monitoring your configured scope.
No verified recent development currently matches strongly enough to require action.
```

Also show:
- what is being watched
- last successful monitoring check/freshness in customer-safe terms
- quick route to Wider Intelligence
- no fake items

But for the standard pilot gate, do not invite a tenant that has no demonstrable First Value.

---

# 14. Meaningful Relevant Monitoring definition

An item counts toward readiness only when it has:

```text
stable identity
meaningful title / what changed
event type
domain
valid evidence/source
effective current/recent date
relevance rationale/context match
```

A domain label alone does not count.

A stale 2023 article presented as current does not count.

A duplicate does not count twice.

---

# 15. Customer freshness language

Expose simple customer-safe freshness:

```text
Updated 18m ago
Monitoring live
3 new since your last visit
Evidence updated 2h ago
```

Do not expose:
- worker names
- SQS
- fan-out
- SQL
- pipeline internals

If monitoring itself is stale, do not falsely show `Live`.

The green `Live` badge must be backed by a real health/freshness condition, not a static UI decoration.

This is a critical acceptance point.

---

# 16. The `Live` badge must become truthful

Observed briefing displays:

```text
● Live
```

while:
- 0 monitoring exists
- no update appeared later

Define `Live` deterministically.

For example, only show healthy live state when:
- core collection heartbeat is within expected window;
- latest Global Intelligence processing is healthy;
- tenant fan-out worker is healthy;
- no blocking queue/backlog state exists.

If the platform cannot know this reliably yet, use a neutral label such as:

```text
Monitoring
```

rather than claiming `Live`.

---

# 17. Since Your Last Visit must prove activity

`0 new developments` is valid only when:
- the query actually ran against a known last-visit timestamp;
- continuous intelligence is functioning;
- no qualifying updates exist.

Test:
- user opens briefing
- create/process new qualifying Global Intelligence
- user returns
- new count increments
- opening/acknowledging behavior updates state correctly

---

# 18. Duplicates and old data must not distort readiness

Before rerunning activation:
- complete the already planned canonical dedup repair
- ensure historical duplicate rows cannot multiply readiness counts
- ensure stale old content cannot count as recent because it was freshly fetched

Readiness uses unique canonical intelligence identity.

---

# 19. Product acceptance — the 30-second value test

A real fintech executive should be able to answer within 30 seconds:

1. What changed that matters to my company?
2. Why does Stem think it matters?
3. Is this something to decide now or simply monitor?
4. What evidence supports it?
5. Can I investigate further?
6. Is Stem continuing to watch after I leave?

If the first screen cannot answer these, the product has not delivered First Value.

---

# 20. Required recovery test tenant

Do not use the already contaminated test tenant as final proof.

Create a fresh realistic staging tenant.

Use:
- valid company context
- several products
- dependency
- competitor
- regulator
- strategic priority
- Decision Lens
- Focus Areas

Do not insert fake customer-visible intelligence.

Run:

```text
provision
→ context
→ entity resolution
→ activation
→ readiness check
→ inspect activation quality
→ invite
→ onboarding
→ personalisation
→ first briefing
→ open monitoring item
→ open dossier
→ inspect evidence
→ ask Cogent
→ wait/process new real staging intelligence
→ confirm continuous update
→ confirm Since Your Last Visit
```

---

# 21. Final acceptance gate

Do not invite real external users until all are true:

```text
[ ] Readiness gate cannot pass empty normal pilot
[ ] First Value Activation uses correct freshness window
[ ] 2023/stale material is not presented as current
[ ] Personalisation finishes or shows honest progress
[ ] First briefing contains meaningful value
[ ] Continuous Intelligence proven after onboarding
[ ] `Live` indicator reflects real health
[ ] Since Your Last Visit proven
[ ] Watchlist parsing bug fixed
[ ] Watchlist shows useful activity state
[ ] Dossier/detail route exists and is reachable
[ ] Dossier includes evidence and historical context
[ ] CIL opens grounded from dossier/intelligence
[ ] Duplicate content does not inflate value
[ ] Fresh test tenant passes 30-second value test
```

---

# 22. Sequencing with UI redesign

Do not use the planned premium UI redesign to mask these issues.

Correct order:

```text
1. Repair value loop
2. Prove fresh pilot value
3. Stabilize continuous intelligence
4. Then apply the new premium UI/COGI redesign
```

The visual redesign should render a working intelligence product beautifully.

It should not decorate an empty one.
