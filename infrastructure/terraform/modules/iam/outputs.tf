output "task_role_arns" {
  description = "Dedicated application task-role ARNs keyed by ECS service name."
  value       = { for service, role in aws_iam_role.task : service => role.arn }
}

output "task_role_names" {
  description = "Dedicated application task-role names keyed by ECS service name."
  value       = { for service, role in aws_iam_role.task : service => role.name }
}

output "execution_role_arns" {
  description = "Dedicated ECS agent execution-role ARNs keyed by ECS service name."
  value       = { for service, role in aws_iam_role.execution : service => role.arn }
}

output "execution_role_names" {
  description = "Dedicated ECS agent execution-role names keyed by ECS service name."
  value       = { for service, role in aws_iam_role.execution : service => role.name }
}

output "service_names" {
  description = "Canonical ECS service names covered by the IAM module."
  value       = sort(tolist(local.services))
}

output "ecr_repository_arns" {
  description = "One of the three canonical ECR repository ARNs assigned to each service execution policy."
  value       = local.ecr_repository_arns
}

output "cloudwatch_log_group_arns" {
  description = "Canonical CloudWatch log-group ARN assigned to each service execution policy."
  value       = local.log_group_arns
}
