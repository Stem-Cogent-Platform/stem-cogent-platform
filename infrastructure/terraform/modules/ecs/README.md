# ECS cluster module

This module provisions the environment ECS cluster named
`sc-cluster-{environment}` with CloudWatch Container Insights enabled.

Both AWS-managed Fargate capacity providers are registered. The default
strategy uses on-demand `FARGATE` with a base task so an availability-sensitive
service cannot inherit Spot capacity accidentally. Fault-tolerant workers may
select `FARGATE_SPOT` explicitly when their ECS services are introduced.

Task definitions, ECS services, autoscaling policies, and ECS Exec are outside
Task 1.3.10 and are intentionally not enabled by this module. Enabling ECS Exec
later also requires its IAM permissions, audit logging, and Systems Manager
Messages network path to be delivered together.
