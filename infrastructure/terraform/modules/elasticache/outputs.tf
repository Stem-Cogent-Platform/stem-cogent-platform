output "replication_group_id" {
  description = "ElastiCache replication group identifier."
  value       = aws_elasticache_replication_group.this.replication_group_id
}

output "arn" {
  description = "ElastiCache replication group ARN."
  value       = aws_elasticache_replication_group.this.arn
}

output "primary_endpoint_address" {
  description = "TLS Redis primary endpoint hostname."
  value       = aws_elasticache_replication_group.this.primary_endpoint_address
}

output "reader_endpoint_address" {
  description = "TLS Redis reader endpoint hostname. A single-node deployment may return the primary endpoint."
  value       = aws_elasticache_replication_group.this.reader_endpoint_address
}

output "port" {
  description = "Redis TLS listener port."
  value       = aws_elasticache_replication_group.this.port
}

output "subnet_group_name" {
  description = "ElastiCache private-data subnet group name."
  value       = aws_elasticache_subnet_group.this.name
}

output "parameter_group_name" {
  description = "Redis parameter group name."
  value       = aws_elasticache_parameter_group.this.name
}

output "cloudwatch_log_group_names" {
  description = "Encrypted CloudWatch Redis engine and slow-log groups."
  value       = { for purpose, group in aws_cloudwatch_log_group.this : purpose => group.name }
}

output "tls_enabled" {
  description = "Whether Redis requires encrypted client transport."
  value       = aws_elasticache_replication_group.this.transit_encryption_enabled
}

output "auth_enabled" {
  description = "Whether a Redis AUTH token is configured."
  value       = aws_elasticache_replication_group.this.auth_token != null
  sensitive   = true
}
