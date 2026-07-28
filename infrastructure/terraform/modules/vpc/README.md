# VPC module

This module creates the two-AZ, three-tier Stem Cogent network, its security
groups and flow logs, and the private AWS service access required by ECS
workloads.

The Task 1.3.11 reference to SC-DOC-009 Section 7.4 is a specification citation
error. The authoritative endpoint definitions are SC-DOC-008 Section 7.4 and
SC-DOC-004 Section 13.2. Their combined service set is implemented as:

- one S3 gateway endpoint associated with all private-app and private-data
  route tables;
- interface endpoints in both private-app subnets for SQS, Secrets Manager,
  KMS, ECR API, ECR Docker, CloudWatch Logs, CloudWatch Metrics, X-Ray, Kinesis
  Data Streams, and SNS; and
- private DNS on every interface endpoint, with HTTPS ingress limited to the
  private-app subnet CIDRs.

ECR requires both `ecr.api` and `ecr.dkr`, and Fargate image layer downloads
also rely on the S3 gateway endpoint. Endpoint policies are intentionally not
used as the authorization boundary: service-specific ECS IAM roles remain the
least-privilege control, while endpoint policies would need to allow shared
AWS-owned resources such as ECR's S3 layer buckets.

DynamoDB is not included because no Stem Cogent specification or workload uses
it. Adding an unused interface or gateway endpoint would create configuration
and cost without completing a platform requirement.
