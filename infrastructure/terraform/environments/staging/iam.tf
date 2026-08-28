module "iam" {
  source = "../../modules/iam"

  aws_account_id             = data.aws_caller_identity.current.account_id
  aws_region                 = var.aws_region
  environment                = var.environment
  project_name               = var.project_name
  resource_prefix            = var.resource_prefix
  queue_arns                 = module.sqs.queue_arns
  bucket_arns                = module.s3.bucket_arns
  bucket_kms_key_arns        = module.s3.kms_key_arns
  secret_arns                = module.secrets.secret_arns
  secrets_kms_key_arn        = module.kms.key_arns["audit"]
  ecr_repository_arns        = module.ecr.repository_arns
  api_log_group_arn          = module.observability.log_group_arns["api"]
  github_repository_id       = "1254005582"
  github_repository_owner_id = "289108209"
  github_environment_name    = "staging"
  github_deployment_ref      = "refs/heads/staging"
}

output "ecs_task_role_arns" {
  description = "Dedicated staging application task-role ARNs keyed by ECS service name."
  value       = module.iam.task_role_arns
}

output "ecs_execution_role_arns" {
  description = "Dedicated staging ECS execution-role ARNs keyed by ECS service name."
  value       = module.iam.execution_role_arns
}
