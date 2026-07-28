output "repository_names" {
  description = "ECR repository names keyed by image class: api, worker, and frontend."
  value       = { for image_class, repository in aws_ecr_repository.this : image_class => repository.name }
}

output "repository_arns" {
  description = "ECR repository ARNs keyed by image class."
  value       = { for image_class, repository in aws_ecr_repository.this : image_class => repository.arn }
}

output "repository_urls" {
  description = "ECR repository URLs keyed by image class."
  value       = { for image_class, repository in aws_ecr_repository.this : image_class => repository.repository_url }
}

output "registry_id" {
  description = "AWS registry ID shared by the three repositories."
  value       = one(toset([for repository in aws_ecr_repository.this : repository.registry_id]))
}
