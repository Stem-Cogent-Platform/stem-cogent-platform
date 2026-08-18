resource "aws_cloudwatch_dashboard" "pipeline_health" {
  dashboard_name = "${var.resource_prefix}-pipeline-health-${var.environment}"

  dashboard_body = jsonencode({
    start          = "-PT24H"
    periodOverride = "inherit"
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "# Pipeline Health — ${upper(var.environment)}\nPhase 1 foundation; future-stage custom metrics are expected to be empty."
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 8
        height = 6
        properties = {
          title   = "Critical DLQ depth"
          view    = "singleValue"
          region  = data.aws_region.current.name
          period  = 60
          stat    = "Maximum"
          metrics = [["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", var.critical_dlq_name]]
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 2
        width  = 8
        height = 6
        properties = {
          title   = "RDS connections"
          view    = "singleValue"
          region  = data.aws_region.current.name
          period  = 60
          stat    = "Maximum"
          metrics = [["AWS/RDS", "DatabaseConnections", "DBInstanceIdentifier", var.rds_instance_identifier]]
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 2
        width  = 8
        height = 6
        properties = {
          title   = "Active pipeline alerts"
          view    = "singleValue"
          region  = data.aws_region.current.name
          period  = 300
          stat    = "Sum"
          metrics = [["StemCogent/Pipeline", "ActiveAlerts", "Environment", var.environment]]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 12
        height = 6
        properties = {
          title   = "Pipeline throughput"
          view    = "timeSeries"
          region  = data.aws_region.current.name
          period  = 3600
          stat    = "Sum"
          metrics = [["StemCogent/Pipeline", "SignalsProcessed", "Environment", var.environment]]
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 12
        height = 6
        properties = {
          title   = "P95 end-to-end latency"
          view    = "timeSeries"
          region  = data.aws_region.current.name
          period  = 300
          stat    = "p95"
          metrics = [["StemCogent/Pipeline", "ProcessingLatencyMs", "Stage", "e2e", "Environment", var.environment]]
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 24
        height = 6
        properties = {
          title   = "Pipeline errors"
          view    = "bar"
          region  = data.aws_region.current.name
          period  = 300
          stat    = "Sum"
          metrics = [["StemCogent/Pipeline", "ProcessingErrors", "Environment", var.environment]]
        }
      },
    ]
  })
}
