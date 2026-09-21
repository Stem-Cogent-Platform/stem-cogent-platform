# Stem Cogent — MVP Product Correction Implementation Sequence
## Codex execution order

This sequence implements the Definitive MVP Product Correction Specification.

Do not run all tracks as one uncontrolled refactor.

## Track 0 — Freeze and baseline
Record branch/commit, run existing backend/frontend/integration tests, record current routes, Cogent path, relevance path, evidence canonicalization, navigation and staging health.

## Track 1 — Relevance quality correction
Implement strong-match requirement, explainable match trace, role-concern matching, geography as supporting factor only, and readiness using the new meaningful-relevance definition.

Tests:
- country-only negative;
- competitor positive;
- dependency positive;
- role-priority positive;
- Focus Area positive;
- nonmatching tenant negative;
- First Value cannot pass on country-only items.

Deploy to staging before continuing.

## Track 2 — Evidence normalization and confidence
Implement canonical source/evidence identity, independent source count, duplicate collapse, shared confidence basis, and prevent Dossier/Cogent confidence contradiction.

## Track 3 — Cogent intent router
Implement:
```text
EXPLAIN
RELEVANCE
EVIDENCE
COMPARE
IMPLICATION
DECISION
RESEARCH
```

Same signal + different questions must produce materially different responses.

## Track 4 — Investigation threads
Persist investigation context: user/tenant, origin object, messages, citations, findings, unresolved questions.

Verify:
```text
How does this affect me?
→ What about.....?
→ Which matters more?
```

## Track 5 — Internal-first retrieval
Before live search, query signal/dossier, related intelligence, entities, Company Context, Decision Lens, Focus Areas and stored evidence. Add an evidence-sufficiency decision.

## Track 6 — Live search integration
Integrate SerpApi or approved provider:
- server-side only;
- secure secret;
- cost/rate limits;
- no private Company Context in provider query;
- result date/source normalization;
- dedup;
- timeout/graceful degradation.

## Track 7 — Live evidence lifecycle
Implement:
```text
EPHEMERAL
INVESTIGATION_EVIDENCE
PROMOTED_INTELLIGENCE
```

No automatic promotion.

## Track 8 — Dossier contract
Refactor existing Dossier projection/UI to:
- Judgment;
- What Changed;
- Why It Matters to You;
- Exposure;
- Implications;
- Decision Posture;
- What We Know;
- What We Do Not Know;
- Related Intelligence;
- Historical Context;
- Sources;
- Investigate with Cogent.

## Track 9 — Decision Brief contract
Refactor projection/UI to:
- Decision;
- Why now;
- What changed;
- Exposure;
- Stakes;
- Decision Paths;
- Trade-offs;
- Validate next;
- Unknowns;
- Owner/timing;
- Evidence.

## Track 10 — Intelligence surface
Rename Wider Intelligence → Intelligence.

Tabs:
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

## Track 11 — Remove Watchlist from primary customer product
Remove nav entry, preserve underlying monitoring data/models, move adjustable scope into Company/Focus Areas, preserve entity pages and redirects.

## Track 12 — Global search / Ask Cogent
Upgrade to:
```text
Search intelligence or ask Cogent…
```

Support internal results, question-to-investigation, and live-search fallback.

## Track 13 — Retention delta
Implement/harden:
```text
new
updated
escalated
new_evidence
new_decision
```

Separate system freshness from user delta.

## Track 14 — Alerts/Digests as delivery
Keep backend delivery; reduce customer emphasis; route back into Briefing/Dossier/Brief.

## Track 15 — Company transparency
Consolidate Company Lens / Company Context into a simpler customer concept: **Company**. No vanity charts.

## Track 16 — Navigation cleanup
Target:
```text
My Briefing
Intelligence
Company

Settings
```

Do not start premium visual redesign yet.

## Track 17 — End-to-end acceptance
Create a fresh realistic Nigerian fintech pilot and test:
1. Company Context;
2. Lens;
3. activation;
4. readiness;
5. invite;
6. onboarding;
7. first briefing;
8. Dossier;
9. relevance question;
10. evidence question;
11. comparison question;
12. decision question;
13. current topic absent from database;
14. live search;
15. follow-up continuity;
16. new signal after user leaves;
17. return;
18. new/updated state.

Do not fake intelligence.

## Track 18 — Closure gate
Return exactly:
```text
MVP PRODUCT CORRECTION READY FOR UI/UX HARDENING
```
or
```text
MVP PRODUCT CORRECTION NOT READY — BLOCKERS REMAIN
```

If blocked, list no more than five core blockers.
