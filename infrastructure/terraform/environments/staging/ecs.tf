locals {
  api_environment_variables = merge(
    {
      DATABASE_HOST               = module.rds.primary_address
      DATABASE_PORT               = tostring(module.rds.port)
      DATABASE_NAME               = module.rds.database_name
      DATABASE_REPLICA_HOST       = coalesce(module.rds.read_replica_address, module.rds.primary_address)
      DATABASE_CREDENTIALS_ARN    = module.secrets.secret_arns["database_credentials"]
      DATABASE_SSL_MODE           = "require"
      REDIS_HOST                  = module.elasticache.primary_endpoint_address
      REDIS_PORT                  = tostring(module.elasticache.port)
      REDIS_AUTH_TOKEN_ARN        = module.secrets.secret_arns["redis_auth_token"]
      REDIS_TLS_ENABLED           = "true"
      JWT_SIGNING_SECRET_ARN      = module.secrets.secret_arns["jwt_signing_secret"]
      PAYSTACK_SECRET_KEY_ARN     = module.secrets.secret_arns["paystack_secret_key"]
      PAYSTACK_PUBLIC_KEY_ARN     = module.secrets.secret_arns["paystack_public_key"]
      PAYSTACK_WEBHOOK_SECRET_ARN = module.secrets.secret_arns["paystack_webhook_secret"]
      SYNTHESIS_ENABLED           = "false"
      CIL_ENABLED                 = "false"
      CLICKHOUSE_ENABLED          = "false"
    },
    {
      for queue_name, queue_url in module.sqs.queue_urls :
      "SQS_${upper(replace(queue_name, "-", "_"))}_URL" => queue_url
    },
    {
      for bucket_name, physical_name in module.s3.bucket_names :
      "S3_${upper(bucket_name)}_BUCKET" => physical_name
    },
  )
}

module "ecs" {
  source = "../../modules/ecs"

  aws_region                 = var.aws_region
  environment                = var.environment
  project_name               = var.project_name
  resource_prefix            = var.resource_prefix
  bootstrap_image_tag        = var.ecs_bootstrap_image_tag
  ecr_repository_urls        = module.ecr.repository_urls
  private_app_subnet_ids     = module.vpc.private_app_subnet_ids
  api_security_group_id      = module.vpc.api_service_security_group_id
  frontend_security_group_id = module.vpc.frontend_service_security_group_id
  api_target_group_arn       = module.alb.api_target_group_arn
  frontend_target_group_arn  = module.alb.frontend_target_group_arn
  task_role_arns             = module.iam.task_role_arns
  execution_role_arns        = module.iam.execution_role_arns
  phase_one_log_group_names = {
    api            = module.observability.log_group_names["api"]
    infrastructure = module.observability.log_group_names["infrastructure"]
    ingestion      = module.observability.log_group_names["ingestion"]
    processing     = module.observability.log_group_names["processing"]
    synthesis      = module.observability.log_group_names["synthesis"]
  }
  api_environment_variables = local.api_environment_variables
}
