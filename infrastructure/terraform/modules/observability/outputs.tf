output "log_group_names" {
  description = "Canonical CloudWatch log group names keyed by operational purpose."
  value       = { for purpose, group in aws_cloudwatch_log_group.this : purpose => group.name }
}

output "log_group_arns" {
  description = "Canonical CloudWatch log group ARNs keyed by operational purpose."
  value       = { for purpose, group in aws_cloudwatch_log_group.this : purpose => group.arn }
}
