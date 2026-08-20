# Stem Cogent ECR module

This module creates the three private repositories used by Application CD:
`sc-api-service-{env}`, `sc-worker-{env}`, and `sc-frontend-{env}`.

All tags are immutable. Application CD therefore publishes only the Git commit
SHA and never publishes a moving `latest` tag. This is the strict implementation
of SC-DOC-010 Task 1.3.12's immutable-release requirement and avoids a mutable
alias silently changing the artefact represented by a deployment.

Each repository uses KMS encryption, scan-on-push, deny-insecure-transport
policy enforcement, and bounded lifecycle retention. By default, KMS uses the
AWS-managed Amazon ECR key so the seven application-data CMKs defined by
SC-DOC-008 Section 2.1 remain purpose-correct. Pass `kms_key_arn` only when a
separately governed ECR CMK has been provisioned.

The lifecycle policy retains the newest 50 tagged releases and removes untagged
layers after seven days. Both values are configurable within validated safety
bounds. Repositories cannot be force-deleted while they contain images.
