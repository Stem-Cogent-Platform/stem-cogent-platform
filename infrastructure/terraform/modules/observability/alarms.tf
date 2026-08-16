resource "aws_cloudwatch_metric_alarm" "rds_connection_saturation" {
  alarm_name          = "sc-rds-connection-saturation"
  alarm_description   = "P1: PostgreSQL connections are at or above 90% of max_connections."
  namespace           = "AWS/RDS"
  metric_name         = "DatabaseConnections"
  dimensions          = { DBInstanceIdentifier = var.rds_instance_identifier }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  datapoints_to_alarm = 3
  threshold           = 180
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false

  tags = merge(local.common_tags, {
    Name     = "sc-rds-connection-saturation"
    Severity = "P1"
  })
}

resource "aws_cloudwatch_metric_alarm" "dlq_critical_depth" {
  alarm_name          = "sc-dlq-critical-depth"
  alarm_description   = "P1: at least one message is visible in the priority-ingestion DLQ."
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  dimensions          = { QueueName = var.critical_dlq_name }
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "missing"
  actions_enabled     = false

  tags = merge(local.common_tags, {
    Name     = "sc-dlq-critical-depth"
    Severity = "P1"
  })
}
