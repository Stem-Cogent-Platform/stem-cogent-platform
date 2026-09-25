# Regulatory engine walkthrough

Implemented the clause-level obligations register, private PDF/DOCX policy vault, 1536-dimensional policy embeddings, multi-document criterion verification, and evidence reviewer inside `/artifacts`. Policy management is at `/settings/policies`; campaign checking is at `/workspace/marketing`.

Assessments use the requested similarity thresholds and verified source excerpts. Reviewer overrides, addenda, and sign-offs have immutable history. Tenant isolation, role permissions, trial gating, versioned documents, and recoverable background jobs are integrated. Marketing suggestions require human review and are not represented as regulatory approval.

Related fixes cover post-commit worker dispatch, tenant scoping, an older migration execution error, removal of fabricated compliance exposure, upload limits, and failed-job recovery. Existing uncommitted context/artifact/workspace/auth prerequisites are included in the application release.

## Verified locally

- Migration chain through 0043 applied to local PostgreSQL with pgvector.
- 12 regulatory integration tests passed, including all five requested flows, tenant isolation, immutable events, reviewer actions, and trial gating. External model/storage calls are mocked in these tests.
- 84 related backend regression tests passed.
- Frontend production build and final TypeScript check passed.
- All 3 browser flows passed: reviewer override, authenticated multipart upload, and campaign highlighting/edit handling.
- Targeted Python lint passed.

## AWS and staging release

Target: staging account `437040615141`, region `eu-west-1`. Discovery confirmed PostgreSQL 16.13, pgvector 0.8.1, 1536-dimensional existing embeddings, and a private, KMS-encrypted, versioned upload bucket. The live database was at migration 0042; discovery found 13 regulatory signals and no intelligence artifacts, so the implementation handles missing full source text explicitly.

Scoped staging S3/KMS/SQS permissions were applied; IAM simulation confirmed API uploads/versioned downloads and worker versioned reads are allowed. Feature-enabled task definitions were registered for API, normalization worker, and scheduler. GitHub Application CD uses the latest task definitions, builds immutable images, runs `alembic upgrade head`, and rolls out staging services.

Per your requested stopping point, deployment completion, migration 0043 on staging, live ECS processing, and populated live assessment SQL are pending verification after the deployment turns green. These are not claimed as passed yet. Production was not deployed or modified in AWS.

## Staging build correction

The first Application CD run failed during worker task imports because the clean container lacked `greenlet`, required by SQLAlchemy async sessions. API and frontend images built successfully; staging migrations and deployment were skipped. The shared requirements now install `SQLAlchemy[asyncio]`, covering both API and worker images. The workflow registry check also explicitly requires both regulatory tasks.
