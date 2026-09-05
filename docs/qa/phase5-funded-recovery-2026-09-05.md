# Phase 5 funded recovery — 2026-09-05

This continuation supersedes the exhausted-credit and undeployed-IAM findings
in the earlier same-day follow-up. It does not constitute production acceptance.

## Verified changes

| Check | Result | Evidence |
|---|---|---|
| Funded OpenAI embedding access | PASS | One tiny request, HTTP 200, task `362c0c956feb4910b7892a7a07c49b90` |
| Staging API provider-secret policy | APPLIED | Saved Terraform plan: zero additions, one in-place API task policy update, zero destroys; apply succeeded |
| Dedicated pre-migration backup | AVAILABLE | RDS snapshot `sc-phase5-pre-0028-20260905`, created September 5 at 10:13:24 UTC |
| Canonical backend baseline | PASS | 325 unit tests, three existing Starlette deprecation warnings |
| Reconciled admin fixtures | PASS | Eight tests; canonical products/priorities now supplied instead of legacy count-only fixtures |
| Initial PR frontend CI | PASS | Run `33960362854` |
| Initial PR Terraform plan | PASS | Run `33960362948` |
| Initial backend CI | FAILED, correction in progress | Run `33960362838`: eight mypy errors in audit output typing and optional profile narrowing; migration step had already passed |

## Replay correctness

- Synthesis locks and cache reads now use separate SQL statements. A statement
  that waits on a transaction advisory lock can retain an earlier snapshot;
  reading after the lock statement gives a fresh READ COMMITTED snapshot.
- Stored exact/semantic duplicates with a separate canonical signal are skipped
  before paid synthesis and before tenant fan-out. Evidence rows are retained.
- Two behavioral unit tests assert that duplicate and completed replay paths
  never construct a paid provider client.
- The explicit claim-index citation prompt is retained from canonical source.

## Release integration

Canonical repository: `stem-cogent-platform`. Local repair commit: `fc86889`.
PR [89](https://github.com/Stem-Cogent-Platform/stem-cogent-platform/pull/89)
targets staging only. A temporary Git worktree under the Windows temporary
directory isolates conflict resolution; it is not a new permanent source clone.
Pre-existing user changes and diagnostic evidence remain untouched.

The integration preserves staging's deployed migration 0023/0026 VARCHAR return
contract and its role constraint correction, plus migration 0027 unchanged.
It preserves live activation dispatch auditing, checkpoint bind-type fixes,
feature gating, physical queue routing, and authentication refresh tests.
Migration 0028 is additive. Do not downgrade a populated environment as cleanup.

## Remaining gate

Clustering remains deliberately at zero; no scored/DLQ bulk replay occurred.
Application deployment, live CIL primary/fallback, current-context activation,
backup-backed historical duplicate remediation, full provider cost ceilings,
and the fresh-tenant continuous-intelligence/delivery/security transcript still
require proof. No production service or production invitation flag was changed.

**NOT READY — BLOCKERS REMAIN**
