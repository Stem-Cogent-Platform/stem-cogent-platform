# ECS cluster module

This module provisions the environment ECS cluster named
`sc-cluster-{environment}` with CloudWatch Container Insights enabled.

Both AWS-managed Fargate capacity providers are registered. The default
strategy uses on-demand `FARGATE` with a base task so an availability-sensitive
service cannot inherit Spot capacity accidentally. Fault-tolerant workers may
select `FARGATE_SPOT` explicitly when their ECS services are introduced.

The module also owns the Phase 1 API/frontend task definitions and services,
plus the one-shot migration task definition introduced by Task 1.3.15. Both
services run in private-app subnets, use on-demand Fargate, attach to ALB IP
target groups, and have deployment circuit-breaker rollback enabled.

Terraform owns the API and frontend task-definition revisions during bootstrap.
After Task 1.5.6 has accepted live Application CD deployments, ownership may
move to Application CD and Terraform can ignore subsequent task-definition
revisions. This prevents an unaccepted deployment workflow from leaving an ECS
service pinned to a failed bootstrap revision.

Only the API and frontend services are created. Pipeline workers remain absent
until their Phase 2 code exists. The two Phase 1 runtime log groups are created
here because ECS cannot start an `awslogs` container when its group is absent;
the later observability module owns the remaining pipeline-wide log inventory.

ECS Exec stays disabled until its IAM permissions, audit logging, and Systems
Manager Messages network path can be delivered together.
