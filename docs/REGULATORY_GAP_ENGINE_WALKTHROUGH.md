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

Final staging closeout (2026-09-25):

- [Application CD run 36147690738](https://github.com/Stem-Cogent-Platform/stem-cogent-platform/actions/runs/36147690738) completed successfully for application commit `403d5d5`.
- API and frontend each have 2/2 running tasks; normalization worker and scheduler each have 1/1. All four rollouts are completed with no pending tasks.
- API `/health/ready` returns HTTP 200; PostgreSQL and Redis are healthy.
- A read-only verification task inside the deployed ECS image confirmed migration `0043`, all five core tables, forced tenant row-level security on policy/chunk/assessment/history tables, the enabled feature flag, and both regulatory task registrations.
- Verification task: `fd989664065943f6a67294c17520a24c`; local evidence: `scratch/regulatory-gap-closeout.json`.

The implementation is deployed and service health is verified. Live end-to-end policy ingestion and populated assessment verification remain unproven: the closeout query found zero extracted obligations. The 12 integration tests verify those workflows locally with mocked external providers; task registration in ECS does not establish successful live processing. Production was not deployed or modified in AWS.

## Staging build correction

The first Application CD run failed during worker task imports because the clean container lacked `greenlet`, required by SQLAlchemy async sessions. API and frontend images built successfully; staging migrations and deployment were skipped. The shared requirements now install `SQLAlchemy[asyncio]`, covering both API and worker images. The workflow registry check also explicitly requires both regulatory tasks.
