# Codex Master Prompt — Stem Cogent MVP Product Correction

Read:
1. `stem-cogent-mvp-product-correction-spec.md`
2. `stem-cogent-mvp-product-correction-implementation-sequence.md`
3. existing V2 source-of-truth docs
4. Phase 5 docs
5. acceptance ledger
6. BUILD_STATUS
7. current staging implementation

This is NOT a rebuild.
This is NOT another broad audit.
This is NOT the premium visual redesign.

Objective:

> Turn external fintech changes into company-specific decision relevance, and let the user investigate what matters through Cogent.

## Work rules

- use only the canonical `stem-cogent-platform` repository;
- do not create duplicate project folders;
- inspect before changing;
- make the smallest production-safe change;
- preserve auth, tenancy, RLS, activation and pipeline infrastructure;
- test after every material alteration;
- stage before production;
- do not fabricate intelligence;
- do not lower relevance thresholds to make screens busy;
- do not add advanced autonomous-agent infrastructure;
- do not begin COGI/premium UI redesign;
- defer non-launch-critical improvements to POST-PILOT BACKLOG.

## Implementation order

Execute the supplied implementation sequence track-by-track.

Do not jump directly to live search before fixing relevance quality.

Do not delete Watchlist data models blindly. Remove Watchlist as a primary customer feature while preserving underlying monitoring scope.

Do not expose private Company Context in live-search provider queries.

Do not automatically promote search results into canonical intelligence.

Do not treat country-only matching as meaningful personalized relevance.

Cogent must support distinct intent behavior and investigation-thread continuity.

## Hard product tests

The implementation is not accepted because APIs return 200.

It passes when a fresh CFO pilot can:
- see genuinely relevant intelligence;
- understand why it matters;
- receive NO_ACTION when something does not materially matter;
- open a structured Dossier;
- ask different questions and get materially different answers;
- continue a multi-turn investigation;
- ask about a current topic absent from Stem;
- trigger internal-first then live-search research;
- receive citations and uncertainty;
- leave and return later to see what changed.

## Final verdict

Return exactly one:

```text
MVP PRODUCT CORRECTION READY FOR UI/UX HARDENING
```

or:

```text
MVP PRODUCT CORRECTION NOT READY — BLOCKERS REMAIN
```

If blocked, list no more than five core blockers.

STOP after the final report.
