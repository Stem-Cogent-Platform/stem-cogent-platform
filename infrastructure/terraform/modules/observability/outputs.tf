output "log_group_names" {
  description = "Canonical CloudWatch log group names keyed by operational purpose."
  value       = { for purpose, group in aws_cloudwatch_log_group.this : purpose => group.name }
}

output "pipeline_health_dashboard_name" {
  description = "CloudWatch Pipeline Health dashboard name."
  value       = aws_cloudwatch_dashboard.pipeline_health.dashboard_name
}

output "p1_alarm_names" {
  description = "Phase 1 P1 CloudWatch alarm names."
  value = [
    aws_cloudwatch_metric_alarm.rds_connection_saturation.alarm_name,
    aws_cloudwatch_metric_alarm.dlq_critical_depth.alarm_name,
  ]
}

output "log_group_arns" {
  description = "Canonical CloudWatch log group ARNs keyed by operational purpose."
  value       = { for purpose, group in aws_cloudwatch_log_group.this : purpose => group.arn }
}
