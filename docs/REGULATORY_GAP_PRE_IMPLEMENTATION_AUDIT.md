# Regulatory gap engine discovery audit — 2026-09-25

The requested Steps A–C already exist in commit `82e0469`; runtime dependencies were corrected in `403d5d5`. This follow-up completes gaps in that implementation. The current user instruction explicitly authorizes implementation after discovery, superseding the approval pause in `prompt.txt`.

## Detected capabilities

- Migration `0005` installs pgvector; `0043` adds the evidence engine. Saved staging discovery records PostgreSQL 16.13, vector 0.8.1 and existing 1536-dimensional `text-embedding-3-small` embeddings. Saved closeout records migration `0043`, but zero obligations. These are previous-run observations, not fresh verification.
- `app/context/policy_service.py` already uses boto3 and the private enterprise-upload bucket, object version IDs and SHA-256 verification. Saved infrastructure discovery reports KMS encryption, public-access blocking and versioning. PDF extraction uses pypdf; DOCX extraction includes paragraphs and tables. No permanent local document store is required.
- The existing bounded OpenAI embedding client is reused with 1536 dimensions. Structured extraction and verification use the configured generation router. External provider errors must remain processing failures, never evidence of regulatory deficiency.
- Existing routes are `frontend/src/app/artifacts`, `settings/policies`, and `workspace/marketing`; this repository does not use the prompt's `(dashboard)` route group. The split-pane reviewer is already embedded in `/artifacts` alongside the existing `ComplianceGapPayload` view.

## Schema strategy

Keep deployed migration `0043_2026_09_25_regulatory_obligations_and_gap_engine.py` intact. It contains complete table definitions and indexes. Tenant identity references `auth.tenants`, not a nonexistent `organizations(id)` table. Signals are partitioned and require the composite `(id, created_at)` foreign key.

| Table | Definition and relations | Indexes/invariants |
| --- | --- | --- |
| `pipeline.regulatory_extractions` | UUID, signal ID/time, source hash/version/URL/text, provider/model, creation time | Unique signal/time/hash/extractor; composite signal FK; retained source snapshot |
| `pipeline.regulatory_obligations` | UUID, extraction and signal identity, clause, title, criteria JSON, departments, excerpt, sanction/deadline, creation time | Unique extraction/clause; composite extraction FK; signal index; nonempty criteria |
| `organizations.tenant_policies` | UUID, tenant/family/title/version, S3 key/version, MIME/checksum/size, category, processing state/error, chunk count, active flag, author, lease/attempts, timestamps | Tenant/author FK; unique family/version; one active version per family; tenant/time index; 20 MB limit |
| `organizations.policy_chunks` | UUID, tenant/policy, ordinal, text/location/token count, vector(1536)/model, creation time | Composite tenant/policy FK; unique policy/ordinal; tenant/policy index; cosine HNSW index; 500-token cap |
| `pipeline.compliance_gap_runs` | UUID, tenant/signal/extraction, idempotency key, state, policy snapshot, engine version, error/attempt/lease, requester/timestamps | Tenant/signal/time index; unique tenant/idempotency key; signal and requester FKs |
| `pipeline.compliance_gap_audits` | UUID, tenant/obligation/run, current and automated status, criterion evidence, score, override, revision/time | Unique tenant/obligation; tenant/status index; same-tenant run FK; status and score checks |
| `audit.compliance_gap_events` | UUID, tenant/audit/actor, event/key/revision, reason/snapshot, addendum policy, timestamp | Same-tenant FKs; unique audit/action key; audit/time index; mutation and truncate rejection triggers; runtime insert/read only |
| `pipeline.marketing_checks` | UUID, tenant/author, copy/channel, result/rules version, creation time | Tenant/time index; same-tenant author FK |

Tenant-owned tables force RLS. Shared public extractions/obligations permit runtime insert/read only. No new schema is needed for the identified corrections.

## Extraction and matching

Public official sources are hydrated when stored signals contain only summaries. Extraction requests 3–10 source-quoted obligations with separately testable criteria. Unsupported quotes and incomplete sources must require source review. Policies are chunked into 500-token windows with 100-token overlap, retaining page/paragraph/table locations. Each criterion retrieves the top three chunks across active tenant policy versions. Similarity below 0.65 means no candidate evidence; adequately met requires every criterion confirmed with quoted evidence above 0.82. Partial and contradicted evidence are reduced deterministically. Instructions treat source/policy text as untrusted data and require verbatim citations.

## Gaps to correct

1. A successful indexing commit is followed by a separate audit-enqueue transaction. Failure or interruption there can leave new policy versions without fresh audits; the error handler can try to mark an already active policy failed, violating its state constraint. Enqueue dependent runs atomically with policy activation.
2. Audit idempotency is check-then-insert and races under concurrent requests. Concurrent runs can finish in the opposite order to creation, overwriting newer assessments. Serialize and order durable jobs consistently.
3. Reviewer endpoints enforce revision checks but do not reject assessments from superseded runs on the server. Apply the latest-run check to every new reviewer action.
4. Health excludes the last completed assessment when a newer run is merely queued or failed, and does not explicitly identify changed policy evidence. Keep completed results and expose staleness.
5. Extraction requests an empty array for insufficient obligations, but schema validation currently marks that as a generic failure. Handle insufficient source support explicitly.
6. Marketing segmentation splits decimal percentages and can miss multiline claims. Add regression coverage and preserve correct highlighted offsets. Editing the channel must also mark displayed results stale.

## Files affected

- Backend: `app/workers/tasks/regulatory_gap.py`, `app/context/gap_auditor.py`, `app/synthesis/obligation_extractor.py`, `app/api/v1/gap_audits.py`, `app/api/v1/policies.py`, `app/context/marketing_checker.py`.
- UI: `frontend/src/lib/compliance.ts`, `frontend/src/app/settings/policies/page.tsx`, `frontend/src/app/workspace/marketing/page.tsx`.
- Verification: `backend/tests/integration/test_regulatory_gap_engine.py`, focused worker tests, `frontend/e2e/regulatory-gap.spec.ts`, and a staging acceptance runner under `backend/app/ops/` if live access is available.

Verification will distinguish local tests with fake providers from real S3/model/pgvector execution inside staging ECS. Existing deployment records alone do not satisfy live ingestion and populated-record acceptance.
