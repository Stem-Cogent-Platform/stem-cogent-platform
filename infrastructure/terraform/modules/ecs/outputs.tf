output "cluster_id" {
  description = "ID of the ECS cluster."
  value       = aws_ecs_cluster.this.id
}

output "cluster_arn" {
  description = "ARN of the ECS cluster."
  value       = aws_ecs_cluster.this.arn
}

output "cluster_name" {
  description = "Name of the ECS cluster."
  value       = aws_ecs_cluster.this.name
}

output "capacity_providers" {
  description = "Fargate capacity providers registered with the cluster."
  value       = aws_ecs_cluster_capacity_providers.this.capacity_providers
}

output "api_service_name" {
  description = "Canonical Phase 1 API ECS service name."
  value       = aws_ecs_service.api.name
}

output "frontend_service_name" {
  description = "Canonical Phase 1 frontend ECS service name."
  value       = aws_ecs_service.frontend.name
}

output "api_task_definition_arn" {
  description = "Terraform bootstrap API task-definition ARN."
  value       = aws_ecs_task_definition.api.arn
}

output "frontend_task_definition_arn" {
  description = "Terraform bootstrap frontend task-definition ARN."
  value       = aws_ecs_task_definition.frontend.arn
}

output "migration_task_definition_arn" {
  description = "One-shot database migration task-definition ARN."
  value       = aws_ecs_task_definition.migration.arn
}

output "migration_task_definition_family" {
  description = "Stable migration task family consumed by Application CD."
  value       = aws_ecs_task_definition.migration.family
}

output "migration_container_name" {
  description = "Migration container selected by Application CD overrides."
  value       = local.migration_container_name
}

output "service_deployments" {
  description = "Phase 1 service/container/image contract consumed by Application CD."
  value       = local.service_deployments
}

output "service_deployments_json" {
  description = "JSON-encoded ECS_SERVICE_DEPLOYMENTS value for the GitHub deployment environment."
  value       = jsonencode(local.service_deployments)
}

output "phase_one_log_group_names" {
  description = "CloudWatch log groups required for Phase 1 tasks to start."
  value       = { for purpose, group in aws_cloudwatch_log_group.phase_one : purpose => group.name }
}
