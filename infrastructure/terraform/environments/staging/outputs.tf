output "vpc_id" {
  description = "ID of the staging VPC."
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs ordered by availability_zones."
  value       = module.vpc.public_subnet_ids
}

output "private_app_subnet_ids" {
  description = "Private application subnet IDs ordered by availability_zones."
  value       = module.vpc.private_app_subnet_ids
}

output "private_data_subnet_ids" {
  description = "Private data subnet IDs ordered by availability_zones."
  value       = module.vpc.private_data_subnet_ids
}

output "private_app_route_table_ids" {
  description = "Private application route table IDs keyed by Availability Zone."
  value       = module.vpc.private_app_route_table_ids
}

output "private_data_route_table_ids" {
  description = "Private data route table IDs keyed by Availability Zone."
  value       = module.vpc.private_data_route_table_ids
}

output "nat_gateway_public_ips" {
  description = "NAT Gateway public IP addresses keyed by Availability Zone."
  value       = module.vpc.nat_gateway_public_ips
}

output "vpc_flow_log_group_name" {
  description = "CloudWatch log group receiving staging VPC Flow Logs."
  value       = module.vpc.flow_log_group_name
}

output "alb_security_group_id" {
  description = "Security group ID for the staging application load balancer."
  value       = module.vpc.alb_security_group_id
}

output "frontend_service_security_group_id" {
  description = "Security group ID for the staging frontend ECS service."
  value       = module.vpc.frontend_service_security_group_id
}

output "api_service_security_group_id" {
  description = "Security group ID for the staging API ECS service."
  value       = module.vpc.api_service_security_group_id
}

output "data_layer_security_group_id" {
  description = "Security group ID for staging PostgreSQL and Redis services."
  value       = module.vpc.data_layer_security_group_id
}

output "vpc_endpoint_ids" {
  description = "Staging VPC endpoint IDs keyed by logical AWS service name."
  value       = module.vpc.vpc_endpoint_ids
}

output "vpc_endpoint_security_group_id" {
  description = "Security group ID protecting the staging AWS interface endpoints."
  value       = module.vpc.vpc_endpoint_security_group_id
}

output "ecs_cluster_name" {
  description = "Name of the staging ECS Fargate cluster."
  value       = module.ecs.cluster_name
}

output "ecs_cluster_arn" {
  description = "ARN of the staging ECS Fargate cluster."
  value       = module.ecs.cluster_arn
}

output "ecr_repository_names" {
  description = "Staging ECR repository names keyed by api, worker, and frontend."
  value       = module.ecr.repository_names
}

output "ecr_repository_arns" {
  description = "Staging ECR repository ARNs keyed by api, worker, and frontend."
  value       = module.ecr.repository_arns
}

output "ecr_repository_urls" {
  description = "Staging ECR repository URLs keyed by api, worker, and frontend."
  value       = module.ecr.repository_urls
}

output "application_cd_build_role_arn" {
  description = "Staging GitHub OIDC role ARN for Application CD image builds."
  value       = module.iam.application_build_role_arn
}

output "application_cd_deploy_role_arn" {
  description = "Staging GitHub OIDC role ARN for Application CD ECS deployments."
  value       = module.iam.application_deploy_role_arn
}

output "application_cd_oidc_subject" {
  description = "Exact GitHub OIDC subject trusted by the staging Application CD roles."
  value       = module.iam.application_cd_oidc_subject
}

output "application_cd_github_environment_variables" {
  description = "Actual Task 1.3.13 values to configure on the staging GitHub Environment."
  value = {
    AWS_APPLICATION_BUILD_ROLE_ARN   = module.iam.application_build_role_arn
    AWS_APPLICATION_DEPLOY_ROLE_ARN  = module.iam.application_deploy_role_arn
    AWS_ACCOUNT_ID                   = data.aws_caller_identity.current.account_id
    ECR_API_REPOSITORY               = module.ecr.repository_names["api"]
    ECR_WORKER_REPOSITORY            = module.ecr.repository_names["worker"]
    ECR_FRONTEND_REPOSITORY          = module.ecr.repository_names["frontend"]
    NEXT_PUBLIC_API_URL              = var.next_public_api_url
    NEXT_PUBLIC_WS_URL               = var.next_public_ws_url
    ECS_CLUSTER_NAME                 = module.ecs.cluster_name
    ECS_MIGRATION_TASK_DEFINITION    = module.ecs.migration_task_definition_family
    ECS_MIGRATION_CONTAINER_NAME     = module.ecs.migration_container_name
    ECS_MIGRATION_SUBNET_IDS         = jsonencode(module.vpc.private_app_subnet_ids)
    ECS_MIGRATION_SECURITY_GROUP_IDS = jsonencode([module.vpc.api_service_security_group_id])
    ECS_SERVICE_DEPLOYMENTS          = module.ecs.service_deployments_json
    API_BASE_URL                     = var.next_public_api_url
  }
}

output "application_cd_pending_github_environment_variables" {
  description = "Application CD value deferred until the first protected endpoint exists."
  value       = ["AUTH_SMOKE_TEST_PATH"]
}

output "public_endpoints" {
  description = "Canonical public Phase 1 HTTPS origins."
  value = {
    api      = module.alb.api_url
    frontend = module.alb.frontend_url
  }
}

output "alb_dns_name" {
  description = "AWS-generated staging ALB DNS name."
  value       = module.alb.load_balancer_dns_name
}

output "alb_target_group_arns" {
  description = "Staging target-group ARNs keyed by Phase 1 service."
  value = {
    api      = module.alb.api_target_group_arn
    frontend = module.alb.frontend_target_group_arn
  }
}

output "alb_certificate_arn" {
  description = "DNS-validated ACM certificate attached to the staging HTTPS listener."
  value       = module.alb.certificate_arn
}

output "alb_web_acl_arn" {
  description = "Regional WAF web ACL protecting the staging ALB."
  value       = module.alb.web_acl_arn
}

output "ecs_phase_one_service_names" {
  description = "Canonical staging ECS service names."
  value = {
    api      = module.ecs.api_service_name
    frontend = module.ecs.frontend_service_name
  }
}

output "ecs_migration_task_definition_arn" {
  description = "Staging one-shot migration task-definition ARN."
  value       = module.ecs.migration_task_definition_arn
}

output "ecs_service_deployments_json" {
  description = "Exact staging ECS_SERVICE_DEPLOYMENTS JSON for Application CD."
  value       = module.ecs.service_deployments_json
}

output "kms_key_arns" {
  description = "Customer-managed KMS key ARNs for the staging environment, keyed by purpose."
  value       = module.kms.key_arns
}

output "kms_alias_names" {
  description = "Customer-managed KMS alias names for the staging environment, keyed by purpose."
  value       = module.kms.alias_names
}

output "s3_bucket_names" {
  description = "S3 bucket names for the staging environment, keyed by purpose."
  value       = module.s3.bucket_names
}

output "s3_bucket_arns" {
  description = "S3 bucket ARNs for the staging environment, keyed by purpose."
  value       = module.s3.bucket_arns
}

output "secret_arns" {
  description = "Secrets Manager ARNs for the staging environment, keyed by application purpose."
  value       = module.secrets.secret_arns
}

output "secret_names" {
  description = "Secrets Manager paths for the staging environment, keyed by application purpose."
  value       = module.secrets.secret_names
}

output "database_primary_host" {
  description = "Private staging PostgreSQL writer hostname."
  value       = module.rds.primary_address
}

output "database_read_replica_host" {
  description = "Private staging PostgreSQL read hostname, or null when the staging replica is disabled."
  value       = module.rds.read_replica_address
}

output "database_port" {
  description = "Staging PostgreSQL listener port."
  value       = module.rds.port
}

output "database_name" {
  description = "Staging PostgreSQL database name."
  value       = module.rds.database_name
}

output "database_credentials_secret_arn" {
  description = "Secrets Manager ARN containing the staging PostgreSQL bootstrap credentials."
  value       = module.secrets.secret_arns["database_credentials"]
}

output "redis_primary_host" {
  description = "Private staging TLS Redis writer hostname."
  value       = module.elasticache.primary_endpoint_address
}

output "redis_reader_host" {
  description = "Private staging TLS Redis reader hostname."
  value       = module.elasticache.reader_endpoint_address
}

output "redis_port" {
  description = "Staging Redis TLS listener port."
  value       = module.elasticache.port
}

output "redis_auth_token_secret_arn" {
  description = "Secrets Manager ARN containing the staging Redis AUTH token."
  value       = module.secrets.secret_arns["redis_auth_token"]
}

output "sqs_queue_names" {
  description = "Primary staging SQS queue names keyed by logical queue name."
  value       = module.sqs.queue_names
}

output "sqs_queue_urls" {
  description = "Primary staging SQS queue URLs keyed by logical queue name."
  value       = module.sqs.queue_urls
}

output "sqs_queue_arns" {
  description = "Primary staging SQS queue ARNs keyed by logical queue name."
  value       = module.sqs.queue_arns
}

output "sqs_dlq_names" {
  description = "Staging SQS dead-letter queue names keyed by logical source queue name."
  value       = module.sqs.dlq_names
}

output "sqs_dlq_urls" {
  description = "Staging SQS dead-letter queue URLs keyed by logical source queue name."
  value       = module.sqs.dlq_urls
}

output "sqs_dlq_arns" {
  description = "Staging SQS dead-letter queue ARNs keyed by logical source queue name."
  value       = module.sqs.dlq_arns
}
output "observability_log_group_names" {
  description = "Canonical application and pipeline CloudWatch log groups."
  value       = module.observability.log_group_names
}
