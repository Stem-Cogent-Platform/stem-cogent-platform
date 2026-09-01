locals {
  api_environment_variables = merge(
    {
      DATABASE_HOST                         = module.rds.primary_address
      DATABASE_PORT                         = tostring(module.rds.port)
      DATABASE_NAME                         = module.rds.database_name
      DATABASE_REPLICA_HOST                 = coalesce(module.rds.read_replica_address, module.rds.primary_address)
      DATABASE_CREDENTIALS_ARN              = module.secrets.secret_arns["database_credentials"]
      DATABASE_SSL_MODE                     = "require"
      DATABASE_RUNTIME_ROLE                 = "sc_app_runtime"
      DATABASE_POOL_SIZE                    = "3"
      DATABASE_MAX_OVERFLOW                 = "2"
      DATABASE_POOL_TIMEOUT_SECONDS         = "10"
      DATABASE_POOL_RECYCLE_SECONDS         = "300"
      FRONTEND_PUBLIC_URL                   = var.frontend_public_url
      REDIS_HOST                            = module.elasticache.primary_endpoint_address
      REDIS_PORT                            = tostring(module.elasticache.port)
      REDIS_AUTH_TOKEN_ARN                  = module.secrets.secret_arns["redis_auth_token"]
      REDIS_TLS_ENABLED                     = "true"
      JWT_SIGNING_SECRET_ARN                = module.secrets.secret_arns["jwt_signing_secret"]
      SYSTEM_ADMIN_MFA_SECRET_ARN           = module.secrets.secret_arns["system_admin_mfa_secret"]
      OPENAI_API_KEY_ARN                    = module.secrets.secret_arns["openai_api_key"]
      GROQ_API_KEY_ARN                      = module.secrets.secret_arns["groq_api_key"]
      RESEND_API_KEY_ARN                    = module.secrets.secret_arns["resend_api_key"]
      PAYSTACK_SECRET_KEY_ARN               = module.secrets.secret_arns["paystack_secret_key"]
      PAYSTACK_PUBLIC_KEY_ARN               = module.secrets.secret_arns["paystack_public_key"]
      PAYSTACK_WEBHOOK_SECRET_ARN           = module.secrets.secret_arns["paystack_webhook_secret"]
      GOOGLE_OAUTH_CREDENTIALS_ARN          = module.secrets.secret_arns["google_oauth_credentials"]
      LINKEDIN_OAUTH_CREDENTIALS_ARN        = module.secrets.secret_arns["linkedin_oauth_credentials"]
      SYNTHESIS_ENABLED                     = "true"
      CIL_ENABLED                           = "true"
      CLICKHOUSE_ENABLED                    = "false"
      PHASE5_PILOT_INVITES_ENABLED          = "false"
      PHASE5_FIRST_VALUE_ACTIVATION_ENABLED = "false"
      PHASE5_BRIEF_LIFECYCLE_ENABLED        = "false"
      PHASE5_DECISION_PATHS_ENABLED         = "false"
      PHASE5_NEW_UI_ENABLED                 = "false"
      PHASE5_PRODUCT_ANALYTICS_ENABLED      = "false"
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
  phase_two_worker_desired_counts = {
    scheduler      = 1
    collector      = 1
    validation     = 1
    normalization  = 1
    classification = 1
    enrichment     = 1
    clustering     = 1
    synthesis      = 1
  }
  phase_one_log_group_names = {
    api            = module.observability.log_group_names["api"]
    infrastructure = module.observability.log_group_names["infrastructure"]
    ingestion      = module.observability.log_group_names["ingestion"]
    processing     = module.observability.log_group_names["processing"]
    synthesis      = module.observability.log_group_names["synthesis"]
  }
  api_environment_variables = local.api_environment_variables
}
