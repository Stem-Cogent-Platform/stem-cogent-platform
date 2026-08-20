mock_provider "aws" {}

variables {
  environment             = "staging"
  logs_kms_key_arn        = "arn:aws:kms:eu-west-1:123456789012:key/01234567-89ab-cdef-0123-456789abcdef"
  rds_instance_identifier = "sc-postgres-staging"
  critical_dlq_name       = "sc-ingestion-priority-dlq-staging"
}

run "creates_pipeline_dashboard_and_p1_alarms" {
  command = plan

  assert {
    condition     = aws_cloudwatch_dashboard.pipeline_health.dashboard_name == "sc-pipeline-health-staging"
    error_message = "Pipeline Health dashboard must use the canonical environment-qualified name."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.rds_connection_saturation.threshold == 180
    error_message = "RDS saturation must alarm at the documented 180-connection threshold."
  }

  assert {
    condition     = aws_cloudwatch_metric_alarm.dlq_critical_depth.threshold == 1
    error_message = "The critical DLQ must alarm when its first message arrives."
  }

  assert {
    condition = alltrue([
      !aws_cloudwatch_metric_alarm.rds_connection_saturation.actions_enabled,
      !aws_cloudwatch_metric_alarm.dlq_critical_depth.actions_enabled,
    ])
    error_message = "Phase 1 alarms must not invoke unconfigured paging actions."
  }
}

run "creates_complete_encrypted_log_inventory" {
  command = plan

  assert {
    condition     = length(aws_cloudwatch_log_group.this) == 7
    error_message = "Observability must own exactly the seven SC-DOC-009 launch log groups."
  }

  assert {
    condition = { for purpose, group in aws_cloudwatch_log_group.this : purpose => group.name } == {
      api            = "/sc/api-service/staging"
      ingestion      = "/sc/pipeline/ingestion/staging"
      processing     = "/sc/pipeline/processing/staging"
      synthesis      = "/sc/pipeline/synthesis/staging"
      delivery       = "/sc/pipeline/delivery/staging"
      dlq            = "/sc/pipeline/dlq/staging"
      infrastructure = "/sc/infrastructure/staging"
    }
    error_message = "Log group names must match the canonical SC-DOC-009 inventory."
  }

  assert {
    condition = { for purpose, group in aws_cloudwatch_log_group.this : purpose => group.retention_in_days } == {
      api            = 90
      ingestion      = 30
      processing     = 30
      synthesis      = 30
      delivery       = 30
      dlq            = 90
      infrastructure = 14
    }
    error_message = "Every log group must use its documented retention tier."
  }

  assert {
    condition = alltrue([
      for group in aws_cloudwatch_log_group.this :
      group.kms_key_id == var.logs_kms_key_arn
    ])
    error_message = "Every application log group must use the environment logs CMK."
  }
}
