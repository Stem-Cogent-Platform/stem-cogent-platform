# AGENTS.md

## Repository Constitution

This file defines the permanent operating rules for any coding agent working in this repository.

It is intentionally short and durable.

It does **not** contain every product detail about Stem Cogent. Product behavior, implementation detail, and current execution state belong in the referenced source-of-truth files.

---

## Canonical Repository

```text
stem-cogent-platform
```

This is the only canonical application repository.

Do not create, maintain, or continue work in duplicate project folders, release-copy folders, temporary fork folders, or parallel implementation directories unless an explicit migration task requires it.

If duplicate folders already exist, do not assume they are safe to delete. Inspect and reconcile first.

---

## Permanent Source-of-Truth Files

### Product source of truth

```text
stem-cogent-mvp-product-correction-spec.md
```

This defines what the current MVP product is supposed to do.

### Implementation sequence

```text
stem-cogent-mvp-product-correction-implementation-sequence.md
```

This defines the required implementation order.

### Current execution track

Before changing code, locate and read the current track, task, status, or active implementation file for the work presently in progress.

Do not assume the next track.

Do not skip ahead.

---

## Mandatory Startup Procedure

Before modifying code:

1. Read `stem-cogent-mvp-product-correction-spec.md`.
2. Read `stem-cogent-mvp-product-correction-implementation-sequence.md`.
3. Read the current active track file or execution note.
4. Inspect `git status`.
5. Inspect `git diff`.
6. Inspect the relevant existing implementation before proposing changes.
7. Run the relevant baseline tests before changing behavior.

If the repository state is dirty, understand the existing modifications before editing.

Do not overwrite unexplained work.

---

## Core Working Rules

- This is **not a rebuild**.
- Do not create duplicate project folders.
- Preserve authentication.
- Preserve tenant isolation.
- Preserve Row Level Security.
- Preserve activation flows.
- Preserve the existing intelligence pipeline infrastructure unless the current track explicitly requires a bounded correction.
- Preserve working functionality unless a documented product correction requires change.
- Never fabricate intelligence, evidence, sources, confidence, relevance, user activity, alerts, or product state.
- Never lower relevance thresholds merely to make screens appear populated.
- Never force Decision Brief creation simply to avoid an empty state.
- Do not jump ahead to another implementation track.
- Make the **smallest production-safe change** that solves the current problem.
- Test every material behavior change.
- Do not deploy directly to production.
- Use staging for validation before production.
- Keep customer-facing behavior aligned with the product specification.
- Keep internal implementation details out of customer-facing copy unless explicitly needed.
- Do not introduce broad architectural rewrites when an existing subsystem can be corrected safely.
- Do not add speculative infrastructure for future features.
- Do not begin premium UI/UX redesign while core product-value corrections remain open.
- Do not add autonomous business-action execution to Cogent.
- Do not expose confidential Company Context to external search providers.
- Do not automatically promote live-search results into canonical intelligence.
- Do not treat geography alone as meaningful personalized relevance.
- Do not hardcode the product around a CFO persona. CFO is an acceptance-test persona, not the architecture.

---

## Product Integrity Rules

Stem Cogent exists to turn external change into company-specific decision relevance.

Any implementation should protect the following truths:

1. The same verified global fact may matter differently to different roles.
2. Personalization must come from Company Context, Decision Lens, Focus Areas, and supported evidence.
3. Relevance must be explainable.
4. A valid signal may correctly result in `NO_ACTION`.
5. Decision Briefs should be rarer than monitoring items.
6. Evidence must be traceable.
7. Duplicate evidence must not masquerade as source diversity.
8. Historical evidence must not be presented as current.
9. “Monitoring checked recently” is not the same as “something relevant changed recently.”
10. User-facing confidence must be internally consistent.

---

## Cogent Rules

Cogent is a bounded intelligence investigation agent, not a generic chatbot.

It must:

- answer the user’s actual question;
- preserve multi-turn investigation context;
- use the active user role;
- use Company Context;
- use the current signal, dossier, brief, entity, or search topic;
- search internal Stem intelligence first;
- use live search only when internal evidence is insufficient, stale, or explicitly requested;
- cite evidence;
- distinguish fact, implication, uncertainty, and next questions;
- be allowed to conclude that something is not materially relevant;
- avoid repeating the same generic answer for different questions.

Different investigation intents should produce materially different behavior.

---

## Live Search Rules

Live search is a discovery layer, not a replacement for the intelligence pipeline.

External search queries must contain only public concepts.

Never send private or confidential Company Context to the external provider.

Live-search evidence must remain in one of these states:

```text
EPHEMERAL
INVESTIGATION_EVIDENCE
PROMOTED_INTELLIGENCE
```

Promotion to canonical intelligence requires validation, deduplication, entity resolution, event classification, date validation, and evidence-quality checks.

---

## Role-Aware Architecture Rule

Do not build role-specific product forks.

Use shared role-aware primitives so that the same intelligence can be interpreted differently for:

- CEO / Founder
- CFO
- COO
- Strategy
- Product
- Compliance / Risk
- other supported Decision Lenses

The facts and citations stay stable.

The ranking, interpretation, exposure, and implications may differ by role.

---

## Testing Discipline

For each material change:

1. reproduce the current behavior;
2. add or update tests where appropriate;
3. implement the smallest safe change;
4. run the narrow relevant tests;
5. run broader regression tests when the change affects shared logic;
6. validate on staging where required;
7. record unresolved issues instead of hiding them.

A passing API response is not sufficient proof of product value.

Acceptance should validate real user outcomes.

---

## Scope Control

If you discover unrelated issues while working on the current track:

- do not automatically expand scope;
- classify whether they block the current track;
- if not blocking, place them in the post-pilot backlog or current issue log;
- continue the current track.

Do not let one task become another full-system audit.

---

## Final Principle

When uncertain, prefer:

```text
inspect
→ understand
→ make the smallest safe correction
→ test
→ validate
```

over:

```text
rewrite
→ expand scope
→ add new architecture
→ hope tests pass
```

The repository should converge toward a reliable product, not accumulate parallel implementations.
