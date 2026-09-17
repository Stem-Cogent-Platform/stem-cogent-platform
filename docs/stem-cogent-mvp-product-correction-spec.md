# Stem Cogent — Definitive MVP Product Correction Specification
## Decision Intelligence for Nigerian Fintech Operators
### Version: MVP Correction / Pre-Pilot Launch Boundary

**Status:** Product source of truth for the next implementation pass  
**Purpose:** Reduce Stem Cogent to the smallest product that reliably delivers company-specific decision intelligence and useful investigation.  
**Important:** This is a product correction, not a rebuild and not a new broad phase.

# 1. The one problem Stem must solve

A fintech operator is surrounded by fragmented external information: regulation, competitor moves, infrastructure incidents, funding and capital moves, customer/market changes, economic changes, expansion signals, and fraud/risk developments.

The problem is not lack of information.

The problem is:

> **Knowing what changed, whether it matters to this company and this decision-maker, why it matters, and what should be considered next.**

Canonical loop:

```text
External change
→ Verify
→ Classify
→ Correlate
→ Match to Company Context
→ Match to Decision Lens / Focus Areas
→ Determine relevance and posture
→ Brief / Dossier
→ Investigate with Cogent
→ Update as new evidence arrives
```

# 2. MVP product promise

> **Cogent continuously understands what is changing around your business, determines what actually matters to you, and helps you investigate what to do next.**

Two modes:

- **Push intelligence:** Stem proactively monitors the world and surfaces what matters.
- **Pull intelligence:** the user asks Cogent about a concern, company, event, market or question. Cogent searches Stem first, then performs live search when internal evidence is insufficient, and returns a structured, cited, role-aware answer.

# 3. MVP feature set — five core capabilities

## 3.1 My Briefing — MUST HAVE
Purpose: **What matters to me right now?**

Contents:
- Requires Attention
- New Since Your Last Visit
- Relevant Monitoring
- Updated Intelligence
- short monitoring-health/freshness indicator

## 3.2 Intelligence — MUST HAVE
Purpose: **What is happening around my business world that I may want to explore?**

Rename customer-facing **Wider Intelligence** to **Intelligence**.

Default view:
```text
For You
```

Domain views:
```text
Regulatory
Competition
Infrastructure
Market & Customers
Financial & Economic
Capital & Partnerships
Expansion
Risk & Trust
```

`For You` is strongly personalized. Domain tabs are broader but still lightly ranked by Company Context and Decision Lens.

## 3.3 Signal Dossier / Decision Brief — MUST HAVE
Signal Dossier: **Understand a development.**  
Decision Brief: **A decision may require attention.**

## 3.4 Investigate with Cogent — MUST HAVE
Cogent is not a generic chatbot. It is a bounded investigation agent that:
- understands the question;
- knows the user's role;
- knows Company Context;
- knows the current signal/dossier/brief/entity;
- remembers the investigation thread;
- retrieves evidence;
- uses live search when needed;
- answers the actual question;
- cites sources;
- states unknowns;
- suggests useful next investigations.

## 3.5 Continuous Delivery & Return Loop — MUST HAVE
Track:
- new intelligence;
- updated intelligence;
- escalated posture;
- new evidence;
- changed Decision Brief;
- alert/digest qualification;
- last acknowledged visit state.

# 4. What is removed or demoted

## 4.1 Watchlist — remove as a primary customer feature
Preserve the underlying monitoring capability.

Replace:
```text
Watchlist
```
with:
```text
Company Context + Focus Areas = Monitoring Scope
```

Entity pages remain available.

## 4.2 Alerts — demote
Keep alert history, delivery preferences and routing. Do not treat Alerts as a core standalone destination.

## 4.3 Digests — demote
Keep briefing history, digest preferences and scheduled delivery.

## 4.4 API / Integrations — hide for guided pilot unless needed
Do not make plan-gated APIs a visible value pillar.

## 4.5 Billing — minimal for guided pilot
Do not make billing a visible product pillar before pilot monetization is ready.

## 4.6 Vanity dashboards / decorative analytics — defer
No charts or widgets without a decision purpose.

# 5. Revised primary navigation

```text
My Briefing
Intelligence
Company

────────────

Settings
```

Cogent is contextual and available across the product.

Global header:
```text
Search intelligence or ask Cogent…
```

# 6. Company Context becomes an enabling layer

Company Context should contain only information that improves relevance:
- company category / business model;
- products;
- operating markets;
- customer segments;
- competitors;
- infrastructure dependencies;
- regulatory exposure;
- strategic priorities;
- active initiatives where available.

Customer-facing labels must not expose internal enum names or version numbers unnecessarily.

# 7. Decision Lens becomes a real role model

A stored role is not enough. The role must change ranking and interpretation.

### CFO
Prioritize revenue exposure, margin, pricing, liquidity, funding, capital allocation, FX, settlement, transaction economics, financial fraud losses, counterparty exposure, expansion economics, regulatory financial consequences.

### COO
Prioritize reliability, disruption, dependency risk, resilience, support impact, execution timing.

### Product
Prioritize product capability, customer behavior, feature implications, technical dependencies, positioning, product response.

### CEO / Strategy
Prioritize market structure, threats, opportunities, competition, expansion, capital, partnerships, regulatory direction.

The global facts do not change; interpretation does.

# 8. Relevance contract — new hard rules

## 8.1 Geography alone is insufficient
A signal cannot count as meaningful personalized monitoring merely because:
```text
signal.country == company.market
```

## 8.2 Meaningful relevance requires at least one strong supported match
Examples:
- configured competitor;
- configured dependency;
- configured regulator / regulatory exposure;
- product exposure;
- customer segment;
- strategic priority;
- Focus Area;
- active initiative;
- role responsibility;
- direct entity relationship;
- explicit industry/business model connection.

## 8.3 Relevance must be explainable
Retain:
```text
why_relevant
matched_context_objects
matched_focus_areas
matched_role_concerns
evidence_strength
```

Bad: `Matches configured Nigeria.`

Good: `Relevant because NexaPay depends on NIBSS Instant Payments and this development concerns settlement reliability.`

## 8.4 First Value readiness
An item counts only if it has:
- current/recent effective date;
- verified evidence;
- stable canonical identity;
- meaningful title/summary;
- event type/domain;
- at least one strong relevance match;
- role/company relevance explanation.

Country-only matches do not count. Duplicates count once. Historical items do not count as current.

# 9. Decision posture

Every personalized intelligence assessment resolves to one of:
```text
NO_ACTION
MONITOR
INVESTIGATE
DECISION_REQUIRED
```

Cogent must be allowed to say a valid signal does not materially matter to this role/company.

# 10. Signal Dossier contract

The dossier must stop behaving like raw database output.

Structure:
1. **Judgment** — one concise intelligence judgment.
2. **What Changed** — verified event.
3. **Why It Matters to You** — specific company/role relevance.
4. **Exposure** — only supported exposure categories.
5. **Implications** — plausible supported consequences.
6. **Decision Posture** — No Action / Monitor / Investigate / Decision Required.
7. **What We Know** — evidence-backed facts.
8. **What We Do Not Know** — gaps and uncertainty.
9. **Related Intelligence** — materially correlated signals.
10. **Historical Context** — clearly labeled.
11. **Sources** — citation-first, not “Open evidence” as the main action.
12. **Investigate with Cogent** — context-preserving entry.

# 11. Decision Brief contract

Creation requires:
```text
meaningful relevance
+
material consequence
+
decision exists
+
sufficient evidence
```

Structure:
```text
Decision
Why now
What changed
Your exposure
What is at stake
Decision paths
Trade-offs
What to validate next
What remains unknown
Owner / timing
Evidence
```

Do not create a Decision Brief merely to avoid an empty screen.

# 12. Cogent investigation architecture

Cogent receives four context layers:
- **User context:** role, responsibilities, relevant preferences.
- **Company context:** products, markets, customers, competitors, dependencies, regulatory exposure, priorities.
- **Current object:** signal, dossier, Decision Brief, entity, or search query.
- **Conversation context:** prior messages, findings, citations, unresolved questions, live-search retrieval.

# 13. Cogent intent router

Support at minimum:
```text
EXPLAIN
RELEVANCE
EVIDENCE
COMPARE
IMPLICATION
DECISION
RESEARCH
```

Different intent must produce different retrieval and response behavior.

# 14. Cogent bounded-agent loop

Suggested maximum:
```text
3–5 retrieval/reasoning/tool steps
```

Loop:
```text
Understand intent
→ identify required information
→ retrieve internal evidence/context
→ determine sufficiency
→ optionally run live search
→ correlate
→ reason against Company Context + role
→ answer
→ cite
→ expose uncertainty
→ suggest next useful investigation
```

Do not autonomously execute business actions.

# 15. Conversation memory / investigation threads

Minimum model:
```text
investigation_id
tenant_id
user_id
origin_type
origin_id
title
messages
retrievals
citations
working_findings
unresolved_questions
created_at
updated_at
```

Follow-up questions must retain thread context.

# 16. Live search architecture

Use an approved search API such as SerpApi as a discovery layer.

Invoke live search when:
- internal evidence is missing;
- internal evidence is stale;
- the user explicitly requests current/latest research;
- comparison requires an entity/event not in Stem;
- the user asks an open research question.

Do not call live search for every message.

# 17. Live search privacy boundary

Never send confidential/private Company Context to the external search provider.

External search receives only public query concepts. Personalization happens inside Stem after retrieval.

# 18. Live search evidence lifecycle

A result has one of:
```text
EPHEMERAL
INVESTIGATION_EVIDENCE
PROMOTED_INTELLIGENCE
```

Promotion requires existing quality gates: trustworthy date, source quality, deduplication, entity resolution, event classification, evidence validation.

# 19. Source strategy

Deliberately cover:
- primary/official regulators, payments infrastructure, exchanges, company announcements;
- credible Nigerian business/financial media;
- credible Nigerian/African technology and fintech media;
- specialist sources;
- live search discovery.

The objective is not maximum URL volume. It is enough high-quality coverage to produce meaningful signals.

# 20. Source quality and corroboration

Normalize evidence by canonical source identity.

Track:
```text
source_count
independent_source_count
primary_source_count
corroboration_strength
```

Do not render repeated copies of the same article as multiple evidence items.

Dossier and Cogent confidence must not contradict without an explicit different confidence dimension. For MVP, prefer one shared intelligence-confidence basis.

# 21. Intelligence feed contract

Cards should show:
- headline;
- one-line judgment/implication;
- domain/event type;
- recency;
- personalized relevance reason if in For You;
- posture;
- source count/citations;
- open dossier.

# 22. Global search / Ask Cogent

Replace passive search with:
```text
Search intelligence or ask Cogent…
```

Entity/topic query → internal matches + option to investigate live.  
Question query → start Cogent investigation.  
Insufficient current evidence → Cogent may invoke live search automatically.

# 23. Retention contract

Track:
```text
new
updated
escalated
new_evidence
new_decision
```

Example:
```text
Since Monday

2 new developments
1 existing assessment updated
1 new source added
0 new decisions
```

# 24. Monitoring freshness versus new relevance

Separate:
```text
Monitoring checked 4m ago
Latest relevant development 2h ago
3 new since your last visit
```

# 25. Alerts and digests as delivery

Alerts/digests bring users back into My Briefing, Dossier or Decision Brief. They are delivery mechanisms, not the core product.

# 26. First-session value contract

Before invite:
- Company Context configured;
- recent intelligence activation complete;
- meaningful relevance available;
- role personalization ready or fast to complete.

After Decision Lens / Focus Areas:
- personal ranking completes;
- briefing contains genuinely relevant monitoring or a Decision Brief.

Country-only items cannot satisfy this gate.

# 27. MVP onboarding correction

For guided pilots, Company Context should mostly be prepared before the user arrives.

User onboarding should focus on:
```text
Who are you?
What do you own?
What matters most right now?
How should important developments reach you?
```

# 28. Success metrics for private pilot

Track:
- onboarding completion;
- time to first meaningful intelligence;
- second-session return;
- briefing open rate;
- dossier open rate;
- Cogent investigation started;
- Cogent follow-up message rate;
- live search usage;
- alert/digest return rate;
- Decision Brief acknowledgment;
- Focus Area change/addition;
- useful/not-useful feedback if implemented.

# 29. Explicitly deferred

Not required before first private pilots:
- dark mode;
- elaborate analytics dashboards;
- scenario simulation;
- advanced autonomous agents;
- complex integrations;
- self-service API platform;
- full billing automation;
- social collaboration;
- complex workflow engine;
- advanced graph visualization;
- every historical source processed;
- every possible role;
- every possible Decision Type.

# 30. Implementation principle

**Reuse:** auth/RLS, Company Context, Decision Lens, Focus Areas, taxonomy, ingestion, freshness, Global Intelligence, activation, Dossier route, Decision Brief model, Cogent service, Groq/OpenAI routing, embeddings, WebSocket/update infrastructure, delivery infrastructure, admin provisioning.

**Correct:** relevance quality, intent routing, investigation threads, live search, source normalization, Dossier, Decision Brief presentation, navigation, retention delta.

**Remove/de-emphasize:** Watchlist UI, standalone Alerts/Digests emphasis, pilot API/Billing clutter.

# 31. MVP acceptance tests

A. CFO relevance — country-only generic news must not count as meaningful relevance.  
B. No-action intelligence — valid but immaterial signal can produce NO_ACTION.  
C. Different role, same evidence — facts/citations stay same, interpretation changes.  
D. Cogent intent — explain/relevance/evidence/compare/decision questions produce materially different answers.  
E. Thread continuity — multi-turn investigation retains context.  
F. Live search — current topic absent from Stem triggers internal-first then live-search research.  
G. Corpus hygiene — live-search results do not automatically become canonical intelligence.  
H. Dossier quality — executive understands judgment, change, relevance, exposure, posture, unknowns and sources quickly.  
I. Retention — new signal updates Since Your Last Visit and existing intelligence can update with new evidence.  
J. Decision Brief rarity — Monitor/Investigate does not automatically create a Decision Brief.

# 32. Final product gate

```text
[ ] Watchlist removed from primary nav
[ ] Intelligence is the broader discovery surface
[ ] My Briefing contains only real personalized relevance
[ ] Geography-only relevance cannot satisfy First Value
[ ] Decision Lens materially changes interpretation
[ ] Dossier uses structured intelligence format
[ ] Decision Brief remains decision-specific
[ ] Cogent supports intent-specific answers
[ ] Cogent supports multi-turn threads
[ ] Live search uses internal-first routing
[ ] Private context is not leaked into external search queries
[ ] Live results do not automatically pollute canonical intelligence
[ ] Evidence is deduplicated
[ ] Confidence is consistent
[ ] New/updated/escalated retention delta works
[ ] Continuous monitoring remains active
[ ] Fresh CFO pilot passes real-value acceptance
```

# 33. MVP definition of done

Stem Cogent MVP is done when a real Nigerian fintech decision-maker can:
1. sign in;
2. immediately see genuinely relevant developments;
3. understand why they matter to role/company;
4. open a structured Dossier;
5. ask Cogent a specific question;
6. get materially different answers to materially different questions;
7. ask follow-ups without losing context;
8. trigger live research when Stem lacks current evidence;
9. see citations and uncertainty;
10. leave;
11. return later and clearly see what changed.

That is the launch boundary.
