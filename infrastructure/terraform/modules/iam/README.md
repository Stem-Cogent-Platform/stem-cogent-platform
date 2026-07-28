# Stem Cogent ECS service IAM

This module creates two dedicated identities for every ECS service. That is
the 16 backend services in SC-DOC-009 Section 5.1 plus the frontend ECS
service required by the later authoritative SC-DOC-010 Tasks 1.3.14 and
1.3.15:

- a **task role**, used only by application code at runtime; and
- an **execution role**, used only by the ECS agent to pull that service's
  image and write that service's log stream.

No role is shared between services. Task policies select only the queues,
secrets, S3 prefixes, and KMS keys required by that service's documented
producer/consumer responsibilities. A collector can write raw payloads but
cannot read them back or delete them; downstream workers can read only the
prefixes they process.

Execution policies use the three canonical image repositories required by
SC-DOC-010 Task 1.3.12 (`api-service`, `frontend`, and shared `worker`) and
the canonical CloudWatch groups from SC-DOC-009 Section 7.2. Services sharing
a log group are restricted to their own log-stream prefix.

All IAM actions are explicit. The few `Resource = "*"` entries are required
by AWS APIs that do not support resource-level authorization:
`cloudwatch:PutMetricData`, `xray:PutTraceSegments`,
`xray:PutTelemetryRecords`, and `ecr:GetAuthorizationToken`. CloudWatch metric
publishing is additionally restricted to the `StemCogent/Pipeline` namespace.
Object resources use prefix wildcards because S3 authorizes objects rather
than prefixes, and runtime-created source/MFA secrets use the narrow naming
paths defined by SC-DOC-008.

The module deliberately does not grant permissions for queues that merely
exist in the 17-queue inventory. `pipeline-scored` and
`pipeline-recommended`, for example, have no producer/consumer in the
authoritative 16-service Phase 1 ECS catalogue. Grant them only when a later
task adds an executable transition.
