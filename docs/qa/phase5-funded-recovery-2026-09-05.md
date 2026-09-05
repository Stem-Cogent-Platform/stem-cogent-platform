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
| Initial backend CI | RESOLVED | Initial run `33960362838` exposed audit typing and optional-profile narrowing errors; subsequent backend run `33960997652` passed 358 unit tests, 75.12% coverage, dependency integration check, migration round-trip, typing and security scans |
| Latest pre-schema release checks | PASS | Backend `33961487629`, frontend `33961487634`, Terraform `33961487631` |
| Full staging Terraform plan | NO CHANGES | Run `33961487631`; clustering pause is codified, not implicitly restored |
| ECS desired-count safeguards | PASS | Six local module tests, including staging zero-count allowance and production zero-count rejection |
| Admin provisioning form | PASS locally | Required canonical context fields submitted; one browser test proves safe failure, retained input, complete retry payload and reset on success |
| CIL strict output schema | 12 targeted tests PASS; live probe pending | Every schema property is now required, including an empty-capable follow-up list |

## Latest continuation

The CIL schema now follows the required-all-properties rule in the
[official OpenAI structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs).
Previously, the defaulted follow-up list was omitted from the schema's required
fields. The regression test checks exact required/property parity and rejects
additional properties. This is a contract correction, not yet proof of live
primary generation.

Two attempts to launch the bounded live probe failed before ECS task creation
because the local Python AWS SSO provider reported an expired, unrefreshable
token. The AWS CLI identity check succeeded for staging account
`437040615141`. An in-memory CLI credential-provider fallback then successfully
launched task `8f2fa50617634aed9a1a8496e08f9246`, but local DNS resolution
failed while polling ECS. Its result and stopped state are unconfirmed.
The task permits one OpenAI request, 160 output tokens, no provider retry, and
no intelligence persistence. Retrieve this task's existing logs after connectivity
returns; do not launch another paid probe merely because polling failed.

Local connectivity also failed for GitHub (`Could not resolve host: github.com`),
AWS STS (connect timeout), and the staging API (name resolution failure).
Both pushes of the schema commit failed. Canonical local commit: `5a5311b`;
integration local commit: `3584512`. Last verified remote head: `a2bf4fe`.
The schema has 12 passing targeted tests and a clean targeted Ruff check.
No PR merge, application deployment, or production mutation occurred.

Entity activity now uses the same source/URL/body identity for both legacy and
fingerprinted rows. Historical evidence has not been deleted or consolidated.

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
