output "primary_identifier" {
  description = "RDS primary DB instance identifier."
  value       = aws_db_instance.primary.identifier
}

output "primary_arn" {
  description = "RDS primary DB instance ARN."
  value       = aws_db_instance.primary.arn
}

output "primary_endpoint" {
  description = "RDS primary PostgreSQL endpoint including port."
  value       = aws_db_instance.primary.endpoint
}

output "primary_address" {
  description = "RDS primary PostgreSQL hostname."
  value       = aws_db_instance.primary.address
}

output "read_replica_identifier" {
  description = "RDS asynchronous read-replica identifier, or null when disabled."
  value       = try(aws_db_instance.read_replica[0].identifier, null)
}

output "read_replica_endpoint" {
  description = "RDS asynchronous read-replica endpoint including port, or null when disabled."
  value       = try(aws_db_instance.read_replica[0].endpoint, null)
}

output "read_replica_address" {
  description = "RDS asynchronous read-replica hostname, or null when disabled."
  value       = try(aws_db_instance.read_replica[0].address, null)
}

output "database_name" {
  description = "Initial PostgreSQL database name."
  value       = var.database_name
}

output "port" {
  description = "PostgreSQL listener port."
  value       = aws_db_instance.primary.port
}

output "subnet_group_name" {
  description = "RDS private-data subnet group name."
  value       = aws_db_subnet_group.this.name
}

output "parameter_group_name" {
  description = "PostgreSQL parameter group name."
  value       = aws_db_parameter_group.this.name
}

output "enhanced_monitoring_role_arn" {
  description = "IAM role used by RDS Enhanced Monitoring."
  value       = aws_iam_role.enhanced_monitoring.arn
}

output "cloudwatch_log_group_names" {
  description = "Encrypted CloudWatch log groups for PostgreSQL and upgrade logs."
  value       = { for purpose, group in aws_cloudwatch_log_group.this : purpose => group.name }
}
