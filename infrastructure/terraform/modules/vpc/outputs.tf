output "vpc_id" {
  description = "ID of the environment VPC."
  value       = aws_vpc.this.id
}

output "vpc_arn" {
  description = "ARN of the environment VPC."
  value       = aws_vpc.this.arn
}

output "vpc_cidr_block" {
  description = "IPv4 CIDR block assigned to the environment VPC."
  value       = aws_vpc.this.cidr_block
}

output "availability_zones" {
  description = "Availability Zones used by the network."
  value       = var.availability_zones
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway attached to the VPC."
  value       = aws_internet_gateway.this.id
}

output "public_subnet_ids" {
  description = "Public subnet IDs ordered to match availability_zones."
  value       = [for availability_zone in var.availability_zones : aws_subnet.public[availability_zone].id]
}

output "public_subnet_ids_by_az" {
  description = "Public subnet IDs keyed by Availability Zone."
  value       = { for availability_zone in var.availability_zones : availability_zone => aws_subnet.public[availability_zone].id }
}

output "private_app_subnet_ids" {
  description = "Private application subnet IDs ordered to match availability_zones."
  value       = [for availability_zone in var.availability_zones : aws_subnet.private_app[availability_zone].id]
}

output "private_app_subnet_ids_by_az" {
  description = "Private application subnet IDs keyed by Availability Zone."
  value       = { for availability_zone in var.availability_zones : availability_zone => aws_subnet.private_app[availability_zone].id }
}

output "private_data_subnet_ids" {
  description = "Private data subnet IDs ordered to match availability_zones."
  value       = [for availability_zone in var.availability_zones : aws_subnet.private_data[availability_zone].id]
}

output "private_data_subnet_ids_by_az" {
  description = "Private data subnet IDs keyed by Availability Zone."
  value       = { for availability_zone in var.availability_zones : availability_zone => aws_subnet.private_data[availability_zone].id }
}

output "public_route_table_id" {
  description = "ID of the public route table."
  value       = aws_route_table.public.id
}

output "private_app_route_table_ids" {
  description = "Private application route table IDs keyed by Availability Zone."
  value       = { for availability_zone in var.availability_zones : availability_zone => aws_route_table.private_app[availability_zone].id }
}

output "private_data_route_table_ids" {
  description = "Private data route table IDs keyed by Availability Zone."
  value       = { for availability_zone in var.availability_zones : availability_zone => aws_route_table.private_data[availability_zone].id }
}

output "nat_gateway_ids" {
  description = "NAT Gateway IDs keyed by Availability Zone."
  value       = { for availability_zone in var.availability_zones : availability_zone => aws_nat_gateway.this[availability_zone].id }
}

output "nat_gateway_public_ips" {
  description = "NAT Gateway Elastic IP addresses keyed by Availability Zone."
  value       = { for availability_zone in var.availability_zones : availability_zone => aws_eip.nat[availability_zone].public_ip }
}

output "flow_log_id" {
  description = "ID of the VPC Flow Log, or null when flow logging is disabled."
  value       = try(aws_flow_log.this[0].id, null)
}

output "flow_log_group_name" {
  description = "CloudWatch log group receiving VPC Flow Logs, or null when flow logging is disabled."
  value       = try(aws_cloudwatch_log_group.vpc_flow_logs[0].name, null)
}

output "alb_security_group_id" {
  description = "Security group ID for the application load balancer."
  value       = aws_security_group.alb.id
}

output "frontend_service_security_group_id" {
  description = "Security group ID for the frontend ECS service."
  value       = aws_security_group.frontend_service.id
}

output "api_service_security_group_id" {
  description = "Security group ID for the API ECS service."
  value       = aws_security_group.api_service.id
}

output "data_layer_security_group_id" {
  description = "Security group ID for PostgreSQL and Redis data services."
  value       = aws_security_group.data_layer.id
}
