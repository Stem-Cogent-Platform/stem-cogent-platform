module "observability" {
  source = "../../modules/observability"

  environment             = var.environment
  project_name            = var.project_name
  resource_prefix         = var.resource_prefix
  logs_kms_key_arn        = module.kms.key_arns["logs"]
  rds_instance_identifier = module.rds.primary_identifier
  critical_dlq_name       = module.sqs.dlq_names["ingestion-priority"]
}

moved {
  from = module.ecs.aws_cloudwatch_log_group.phase_one["api"]
  to   = module.observability.aws_cloudwatch_log_group.this["api"]
}

moved {
  from = module.ecs.aws_cloudwatch_log_group.phase_one["infrastructure"]
  to   = module.observability.aws_cloudwatch_log_group.this["infrastructure"]
}
