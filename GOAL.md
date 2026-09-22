# GOAL.md

## Stem Cogent — End-to-End Product Goal

This file defines the end-to-end product outcome we are trying to achieve.

It describes the product as a real user should experience it.

It is not an implementation sequence and it is not a sprint checklist.

The implementation sequence explains **how to get there**.

This file explains **what “there” actually means**.

---

# 1. Product Goal

Stem Cogent should help a fintech decision-maker understand a changing external environment without having to manually piece together fragmented news, regulatory updates, competitor activity, infrastructure developments, market signals, funding events, and economic information.

The product must answer:

> **What changed?**

> **Does it matter to my company?**

> **Does it matter to me in my role?**

> **Why?**

> **What is exposed?**

> **What is at stake?**

> **Do I need to act, investigate, monitor, or ignore it?**

> **What evidence supports that judgment?**

> **What remains uncertain?**

> **What should I investigate next?**

The product should reduce information overload, not add to it.

---

# 2. The Real User Experience We Want

Imagine a real fintech operator signs in.

The product already understands enough about the company to be useful.

It knows, where configured and verified:

- the company’s business model;
- products;
- markets;
- customer segments;
- competitors;
- infrastructure dependencies;
- regulatory exposure;
- strategic priorities;
- active focus areas.

It also understands the user’s Decision Lens.

For example:

- CFO;
- CEO;
- COO;
- Strategy;
- Product;
- Compliance / Risk.

The same external event may be interpreted differently depending on who is looking at it.

A CFO should not receive the same explanation as a Product Lead.

A Product Lead should not receive the same explanation as a COO.

The global fact remains the same.

The decision relevance changes.

---

# 3. The One Core Product Loop

The entire MVP should support this loop:

```text
The world changes
        ↓
Stem detects or discovers the change
        ↓
Stem verifies and structures the evidence
        ↓
Stem classifies and correlates the change
        ↓
Stem compares it against Company Context
        ↓
Stem compares it against Decision Lens and Focus Areas
        ↓
Stem determines whether it matters
        ↓
Stem assigns a decision posture
        ↓
The user receives structured intelligence
        ↓
The user can investigate deeper with Cogent
        ↓
New evidence arrives
        ↓
Stem updates the intelligence
        ↓
The user returns because something changed
```

Everything in the MVP should strengthen this loop.

---

# 4. The Two Ways Users Get Value

Stem Cogent must work in two complementary modes.

## 4.1 Push Intelligence

Stem monitors the external environment continuously.

The user does not have to know what to search for.

The product proactively surfaces what matters.

Examples:

- a regulator issues a new rule;
- a competitor changes pricing;
- a payment rail has a reliability incident;
- a bank changes a partnership;
- a major fintech enters a new market;
- funding or capital conditions shift;
- a new fraud or trust issue emerges.

Stem should decide whether that development matters to the specific company and user.

If it does not matter, it should not be forced into the user’s briefing.

## 4.2 Pull Intelligence

The user may already have a concern in mind.

They should be able to ask Cogent.

Examples:

> What does this mean for us?

> How does this affect me as CFO?

> What are the detailed provisions?

> Compare this with what Moniepoint is doing.

> Could this affect our margins?

> What should we consider doing?

> What does the Dangote IPO mean for a Nigerian payments company like ours?

Cogent should first search Stem’s existing intelligence.

If Stem lacks enough current evidence, Cogent should perform live search, retrieve current sources, correlate them, and answer the question through the user’s Company Context and Decision Lens.

This should feel like speaking to an informed analyst who understands both the external market and the company context.

---

# 5. Primary MVP Product Surfaces

The customer-facing MVP should be small.

## 5.1 My Briefing

Purpose:

> **What matters to me right now?**

This is the personalized command center.

It should show only meaningful intelligence.

Possible sections:

- Requires Attention
- New Since Your Last Visit
- Relevant Monitoring
- Updated Intelligence

The briefing should not be a generic news feed.

It should not fill space for appearance.

If nothing requires a decision, it may truthfully say:

```text
0 decisions require your attention
```

But the page should still make clear whether:

- new relevant developments exist;
- monitored intelligence changed;
- additional evidence arrived;
- nothing material changed.

Zero decisions can be a useful outcome.

Zero useful intelligence is not the product goal.

---

# 6. Intelligence

Purpose:

> **What is happening around my business world that I may want to explore?**

This is broader than My Briefing.

It should feel like a high-quality intelligence feed.

The user can browse:

```text
For You
Regulatory
Competition
Infrastructure
Market & Customers
Financial & Economic
Capital & Partnerships
Expansion
Risk & Trust
```

`For You` should be strongly personalized.

The domain views can be broader.

The user should be able to explore an area intentionally even when no immediate decision is required.

Examples:

- a CFO opens Capital & Partnerships;
- a Strategy Lead opens Expansion;
- a Product Lead opens Competition;
- a COO opens Infrastructure;
- a Compliance Lead opens Regulatory.

The system should still rank what is likely to matter to that user.

---

# 7. Watchlist Is Not a Core Product

The user should not have to maintain a separate Watchlist that duplicates known company context.

Monitoring scope should come from:

```text
Company Context
+
Focus Areas
=
Monitoring Scope
```

If the company already knows that Moniepoint is a competitor, NIBSS is a dependency, and CBN is a regulator, the user should not have to “watch” them again manually.

Entity pages may remain useful for exploration.

But Watchlist should not be a primary customer product.

---

# 8. Signal Dossier

When the user opens a development, they should not see a metadata dump.

They should see structured intelligence.

The Dossier should answer:

## Judgment

What is the intelligence judgment?

## What Changed

What actually happened?

## Why It Matters to You

Why does this matter to this company and this role?

If direct relevance is not established, say so.

## Exposure

What is touched?

Examples:

- product;
- market;
- dependency;
- regulator;
- financial exposure;
- customer segment;
- competitor;
- operations.

## Implications

What could this mean?

Only supported implications.

Do not invent outcomes.

## Decision Posture

One of:

```text
NO_ACTION
MONITOR
INVESTIGATE
DECISION_REQUIRED
```

## What We Know

Evidence-backed facts.

## What We Do Not Know

Uncertainties and evidence gaps.

## Related Intelligence

Only developments that materially change interpretation.

## Historical Context

Older relevant events clearly marked as historical.

## Sources

Citations and evidence.

The intelligence comes first.

The evidence supports it.

## Investigate with Cogent

The user should be able to continue from the Dossier directly into a contextual investigation.

---

# 9. Decision Brief

A Decision Brief is not just a longer signal.

It exists only when a decision may genuinely require attention.

A Decision Brief should answer:

```text
What decision is being considered?
Why now?
What changed?
What is our exposure?
What is at stake?
What options or paths exist?
What are the trade-offs?
What do we still need to validate?
What remains unknown?
Who should own the decision?
What evidence supports this?
```

Decision Briefs should be rarer and more valuable than monitoring items.

Do not create them to fill empty screens.

---

# 10. Cogent Investigation Agent

Cogent should behave like a bounded intelligence analyst.

It is not a generic chat assistant.

It should know:

- who the user is;
- their role;
- their company;
- the current signal or Dossier;
- previous messages in the investigation;
- previously retrieved evidence;
- unresolved questions.

Cogent should support different investigation intents.

At minimum:

```text
EXPLAIN
RELEVANCE
EVIDENCE
COMPARE
IMPLICATION
DECISION
RESEARCH
```

A user asking:

> What happened?

should not receive the same answer structure as:

> What should we do?

A user asking:

> What are the detailed provisions?

should receive evidence extraction, not a generic decision paragraph.

A user asking:

> Compare this with Moniepoint.

should trigger comparison behavior.

Different questions must produce different answers.

---

# 11. Multi-Turn Investigation

Conversation continuity is essential.

Example:

```text
User: How does this affect me as CFO?
Cogent: ...
User: What about Moniepoint?
Cogent: ...
User: Which matters more?
Cogent: ...
```

The final question must understand the previous context.

Cogent should not restart from the original signal every turn.

It should feel like an ongoing investigation.

---

# 12. Internal Intelligence First, Live Search Second

Cogent should not search the web for everything.

The sequence should be:

```text
User question
        ↓
Understand intent
        ↓
Search Stem intelligence
        ↓
Search existing evidence
        ↓
Search related intelligence/entities
        ↓
Is evidence sufficient and current?
        │
        ├── Yes → answer
        │
        └── No
              ↓
          Live search
              ↓
          retrieve sources
              ↓
          validate and deduplicate
              ↓
          correlate evidence
              ↓
          apply Company Context + Decision Lens
              ↓
          structured answer
```

This preserves cost, speed, and trust.

---

# 13. Live Search

Live search is required because users will ask questions Stem has not already captured.

Example:

A CFO asks:

> What does the Dangote IPO mean for us?

If the internal corpus lacks enough current evidence, Cogent should search live public sources.

The external search provider should receive only public search concepts.

It should never receive confidential Company Context.

Private personalization happens after retrieval inside Stem.

Live-search results should not automatically enter the canonical intelligence corpus.

They may remain:

```text
EPHEMERAL
```

or:

```text
INVESTIGATION_EVIDENCE
```

Only validated results should become:

```text
PROMOTED_INTELLIGENCE
```

---

# 14. Nigerian Source Coverage

The product should not depend on only a few sources.

Stem should deliberately cover enough credible Nigerian and relevant African sources to capture meaningful change.

This should include:

- primary regulators;
- payments infrastructure;
- official filings;
- company announcements;
- credible business and financial media;
- credible fintech and technology media;
- specialist industry sources;
- live-search discovery for gaps.

The goal is not maximum crawling volume.

The goal is useful coverage.

Ten high-quality sources that reliably produce relevant signals are more valuable than hundreds of noisy URLs.

---

# 15. Relevance Quality

A signal is not meaningful simply because it happened in Nigeria.

Geography can support relevance.

It cannot define relevance by itself.

Meaningful relevance should come from supported connection to things such as:

- competitor;
- dependency;
- regulator;
- product;
- customer segment;
- strategic priority;
- Focus Area;
- active initiative;
- role responsibility;
- direct entity relationship;
- business-model exposure.

The system should be able to explain why something is relevant.

Bad:

> Relevant because it happened in Nigeria.

Good:

> Relevant because your company depends on NIBSS Instant Payments and this development concerns settlement reliability.

---

# 16. Role-Aware Intelligence

Role personalization must be real.

Example:

The same infrastructure signal may produce:

### CFO

> possible settlement-cost, liquidity, transaction-volume, or financial exposure.

### COO

> reliability, service continuity, vendor dependency, and operational resilience exposure.

### Product

> customer experience, product capability, or feature-delivery implications.

The facts remain the same.

The interpretation changes.

The product must not be hardcoded around CFO.

CFO is only a strong acceptance persona.

---

# 17. Source and Evidence Quality

Evidence should strengthen trust.

Repeated copies of the same article should not appear as independent corroboration.

Stem should distinguish:

- number of source records;
- number of independent sources;
- number of primary sources;
- corroboration strength.

Confidence should be consistent between Dossier and Cogent.

If confidence means different things in different components, the distinction must be explicit.

For MVP, one shared intelligence-confidence basis is preferred.

---

# 18. Retention

The user must have a reason to return.

The retention hook is not:

- a dashboard;
- a watchlist;
- a chatbot;
- decorative analytics.

The retention hook is:

> **The world changed while I was doing my job, and Stem noticed what mattered before I had to go looking for it.**

When the user returns, they should clearly understand what changed since their last acknowledged state.

Example:

```text
Since Monday

2 new developments
1 intelligence assessment updated
1 new evidence source added
0 new decisions
```

Stem should also distinguish:

```text
Monitoring checked 4m ago
Latest relevant development 2h ago
3 new since your last visit
```

System freshness and user-value change are not the same thing.

---

# 19. Alerts and Digests

Alerts and digests are delivery mechanisms.

They should bring the user back into:

- My Briefing;
- a Dossier;
- a Decision Brief.

Example alert:

> NIBSS reliability moved from Monitor to Investigate after two additional verified incidents.

Example digest:

```text
Your CFO Briefing

1 needs investigation
3 new developments
2 intelligence items updated
0 new decisions
```

Alerts and Digests do not need to be major standalone product destinations.

---

# 20. Company

The Company area should answer:

> **What does Stem currently understand about us?**

It should make Company Context transparent and correctable.

Possible sections:

- company profile;
- business model;
- products;
- markets;
- customers;
- competitors;
- dependencies;
- regulatory exposure;
- strategic priorities;
- Focus Areas.

No decorative charts are required.

The purpose is trust and correction.

---

# 21. Fast Time to Value

For guided pilots, the company should be prepared before the invited executive arrives.

The user should not be asked to rebuild obvious Company Context manually.

The user onboarding should mostly answer:

```text
Who are you?
What do you own?
What matters most right now?
How should important developments reach you?
```

The user should reach a useful briefing quickly.

---

# 22. What Success Looks Like for a Real User

A successful end-to-end experience looks like this:

1. The company is provisioned.
2. Company Context is valid.
3. Recent intelligence activation runs.
4. A real user receives an invitation.
5. The user chooses their role and Focus Areas.
6. The user lands on My Briefing.
7. The briefing contains genuinely relevant intelligence.
8. The user understands why each item matters.
9. The user opens a Dossier.
10. The Dossier provides structured intelligence, not raw metadata.
11. The user asks Cogent a specific question.
12. Cogent answers that question rather than repeating a generic summary.
13. The user asks a follow-up.
14. Cogent preserves the thread.
15. The user asks about a current topic not in Stem.
16. Cogent searches internal intelligence first.
17. Cogent performs live search because internal evidence is insufficient.
18. Cogent returns a structured, cited, role-aware investigation.
19. The user leaves.
20. New external evidence arrives later.
21. Stem reassesses the relevant intelligence.
22. The user receives a useful alert or sees a change on return.
23. The user immediately understands what is new, updated, or escalated.

That is the product.

---

# 23. MVP Navigation Goal

Primary customer navigation:

```text
My Briefing
Intelligence
Company

────────────

Settings
```

Cogent should be available contextually throughout the product.

The global search can become:

```text
Search intelligence or ask Cogent…
```

---

# 24. What We Are Not Trying to Perfect Before Pilot

The private pilot does not require:

- dark mode;
- advanced dashboards;
- every integration;
- self-service API platform;
- full billing automation;
- autonomous action-taking agents;
- every historical signal processed;
- every possible role;
- every possible Decision Type;
- complex collaboration workflows;
- elaborate visualization;
- perfect mobile behavior across every device;
- every possible source.

The MVP must first deliver reliable decision intelligence.

---

# 25. Product Definition of Done

Stem Cogent is ready for private pilot when a real decision-maker can:

```text
sign in
→ see what genuinely matters
→ understand why it matters
→ inspect structured intelligence
→ ask deeper questions
→ receive intent-aware answers
→ continue a multi-turn investigation
→ trigger live research when needed
→ see evidence and uncertainty
→ leave
→ return later
→ clearly understand what changed
```

The product is not done because all endpoints exist.

The product is done when this value loop works reliably enough that a real user can experience it without the team explaining what the software was supposed to do.

---

# 26. Final Principle

Stem should not behave like:

```text
news feed
+
database
+
generic chatbot
```

It should behave like:

```text
continuous external intelligence
+
company-specific relevance
+
role-specific interpretation
+
structured decision support
+
bounded live investigation
```

That is the end-to-end goal.
