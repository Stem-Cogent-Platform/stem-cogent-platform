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

### Staging rollout and authenticated verification

Connectivity recovered; the interrupted contract probe's existing CloudWatch
log reports HTTP 200, exact title grounding and a valid citation with
`gpt-4.1-mini-2025-04-14` (181 input + 69 output = 250 tokens). No repeat
request was needed. PR #89 merged at `16d3f0e`; Application CD
`33991785563` and Infrastructure CD `33991785579` succeeded.
Pre-merge backend CI `33991558761` passed 360 unit tests, 75.33% coverage,
the one PostgreSQL/Redis dependency integration check, migration round-trip
and security/type checks.

Post-deployment task `20027aeb04b14beaa8d459b3d6bb83cf` verified:

- Database head `0028`; diagnostic context version 6.
- API revision 66 and frontend revision 54 have completed rollouts, 2/2 each.
  Clustering revision 27 remains deliberately 0/0.
- Live/ready, auth/me, context/company, company, team and Paystack entity
  endpoints return 200. Both company surfaces return 29 context objects.
- Tenant ADMIN receives 403 from internal-admin tenants.
- Paystack activity returns 29 items; no historical evidence rows were deleted.
- Current-context relevant monitoring is zero; this does not pass first value.
- CIL returns 200 with an answer and one citation, but query-log attribution is
  `deterministic / structured-retrieval-v1`, latency 214 ms. This is graceful
  degradation, not a pass for normal OpenAI generation.

The additional CIL defect is JSON encoding: retrieval retains UUID, datetime
and Decimal database values, while both provider clients use plain
`json.dumps`. Two HTTP-transport regression cases reproduced deterministic
fallback before the fix. Encoding at the CIL boundary makes primary and
fallback cases pass. PR #90 carries this correction; its live proof is pending.

The post-merge infrastructure plan also observed the scheduler's temporary
migration pause and restored desired count 0 to 1 (one change, no destroys).
This overlapped Application CD. The corrective workflow change shares one
non-cancelling queue between infrastructure and application workflows, using
[GitHub's documented concurrency queue](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency).
This is separate from the permanent clustering pause, which was preserved.

The user delegated the fresh pilot choice. Proposed controlled staging profile:
Paystack, reserved example email, public payment-products context from
[Paystack](https://paystack.com/). It is not an actual Paystack customer invitation;
no email will be sent externally. Fresh tenant creation has not occurred.
Provisioning requires the real SYSTEM_ADMIN password-plus-MFA flow; no MFA
claims will be fabricated and no role/password reset is authorized by this plan.

Clustering remains deliberately at zero; no scored/DLQ bulk replay occurred.
Application deployment, live CIL primary/fallback, current-context activation,
backup-backed historical duplicate remediation, full provider cost ceilings,
and the fresh-tenant continuous-intelligence/delivery/security transcript still
require proof. No production service or production invitation flag was changed.

**NOT READY — BLOCKERS REMAIN**
