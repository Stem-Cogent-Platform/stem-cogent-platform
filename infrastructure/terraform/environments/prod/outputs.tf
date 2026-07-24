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
