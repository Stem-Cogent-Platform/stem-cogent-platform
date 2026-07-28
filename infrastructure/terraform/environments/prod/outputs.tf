output "vpc_id" {
  description = "ID of the production VPC."
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
  description = "CloudWatch log group receiving production VPC Flow Logs."
  value       = module.vpc.flow_log_group_name
}

output "alb_security_group_id" {
  description = "Security group ID for the production application load balancer."
  value       = module.vpc.alb_security_group_id
}

output "frontend_service_security_group_id" {
  description = "Security group ID for the production frontend ECS service."
  value       = module.vpc.frontend_service_security_group_id
}

output "api_service_security_group_id" {
  description = "Security group ID for the production API ECS service."
  value       = module.vpc.api_service_security_group_id
}

output "data_layer_security_group_id" {
  description = "Security group ID for production PostgreSQL and Redis services."
  value       = module.vpc.data_layer_security_group_id
}

output "kms_key_arns" {
  description = "Customer-managed KMS key ARNs for the production environment, keyed by purpose."
  value       = module.kms.key_arns
}

output "kms_alias_names" {
  description = "Customer-managed KMS alias names for the production environment, keyed by purpose."
  value       = module.kms.alias_names
}

output "s3_bucket_names" {
  description = "S3 bucket names for the production environment, keyed by purpose."
  value       = module.s3.bucket_names
}

output "s3_bucket_arns" {
  description = "S3 bucket ARNs for the production environment, keyed by purpose."
  value       = module.s3.bucket_arns
}

output "secret_arns" {
  description = "Secrets Manager ARNs for the production environment, keyed by application purpose."
  value       = module.secrets.secret_arns
}

output "secret_names" {
  description = "Secrets Manager paths for the production environment, keyed by application purpose."
  value       = module.secrets.secret_names
}

output "database_primary_host" {
  description = "Private production PostgreSQL writer hostname."
  value       = module.rds.primary_address
}

output "database_read_replica_host" {
  description = "Private production PostgreSQL asynchronous read hostname."
  value       = module.rds.read_replica_address
}

output "database_port" {
  description = "Production PostgreSQL listener port."
  value       = module.rds.port
}

output "database_name" {
  description = "Production PostgreSQL database name."
  value       = module.rds.database_name
}

output "database_credentials_secret_arn" {
  description = "Secrets Manager ARN containing the production PostgreSQL bootstrap credentials."
  value       = module.secrets.secret_arns["database_credentials"]
}

output "redis_primary_host" {
  description = "Private production TLS Redis writer hostname."
  value       = module.elasticache.primary_endpoint_address
}

output "redis_reader_host" {
  description = "Private production TLS Redis reader hostname."
  value       = module.elasticache.reader_endpoint_address
}

output "redis_port" {
  description = "Production Redis TLS listener port."
  value       = module.elasticache.port
}

output "redis_auth_token_secret_arn" {
  description = "Secrets Manager ARN containing the production Redis AUTH token."
  value       = module.secrets.secret_arns["redis_auth_token"]
}

output "sqs_queue_names" {
  description = "Primary production SQS queue names keyed by logical queue name."
  value       = module.sqs.queue_names
}

output "sqs_queue_urls" {
  description = "Primary production SQS queue URLs keyed by logical queue name."
  value       = module.sqs.queue_urls
}

output "sqs_queue_arns" {
  description = "Primary production SQS queue ARNs keyed by logical queue name."
  value       = module.sqs.queue_arns
}

output "sqs_dlq_names" {
  description = "Production SQS dead-letter queue names keyed by logical source queue name."
  value       = module.sqs.dlq_names
}

output "sqs_dlq_urls" {
  description = "Production SQS dead-letter queue URLs keyed by logical source queue name."
  value       = module.sqs.dlq_urls
}

output "sqs_dlq_arns" {
  description = "Production SQS dead-letter queue ARNs keyed by logical source queue name."
  value       = module.sqs.dlq_arns
}
