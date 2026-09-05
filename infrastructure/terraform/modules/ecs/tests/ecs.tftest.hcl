mock_provider "aws" {
  mock_resource "aws_ecs_cluster" {
    defaults = {
      id  = "arn:aws:ecs:eu-west-1:123456789012:cluster/sc-cluster-staging"
      arn = "arn:aws:ecs:eu-west-1:123456789012:cluster/sc-cluster-staging"
    }
  }
}

variables {
  aws_region          = "eu-west-1"
  environment         = "staging"
  bootstrap_image_tag = "0123456789abcdef0123456789abcdef01234567"

  ecr_repository_urls = {
    api      = "123456789012.dkr.ecr.eu-west-1.amazonaws.com/sc-api-service-staging"
    worker   = "123456789012.dkr.ecr.eu-west-1.amazonaws.com/sc-worker-staging"
    frontend = "123456789012.dkr.ecr.eu-west-1.amazonaws.com/sc-frontend-staging"
  }

  private_app_subnet_ids     = ["subnet-0123456789abcdef0", "subnet-0123456789abcdef1"]
  api_security_group_id      = "sg-0123456789abcdef0"
  frontend_security_group_id = "sg-0123456789abcdef1"
  api_target_group_arn       = "arn:aws:elasticloadbalancing:eu-west-1:123456789012:targetgroup/sc-api-tg-staging/abc"
  frontend_target_group_arn  = "arn:aws:elasticloadbalancing:eu-west-1:123456789012:targetgroup/sc-frontend-tg-staging/def"
  phase_one_log_group_names = {
    api            = "/sc/api-service/staging"
    infrastructure = "/sc/infrastructure/staging"
    ingestion      = "/sc/pipeline/ingestion/staging"
    processing     = "/sc/pipeline/processing/staging"
    synthesis      = "/sc/pipeline/synthesis/staging"
  }

  task_role_arns = {
    api-service           = "arn:aws:iam::123456789012:role/stem-cogent/sc-api-service-staging-task"
    frontend-service      = "arn:aws:iam::123456789012:role/stem-cogent/sc-frontend-service-staging-task"
    scheduler-worker      = "arn:aws:iam::123456789012:role/stem-cogent/sc-scheduler-worker-staging-task"
    collector-worker      = "arn:aws:iam::123456789012:role/stem-cogent/sc-collector-worker-staging-task"
    validation-worker     = "arn:aws:iam::123456789012:role/stem-cogent/sc-validation-worker-staging-task"
    normalization-worker  = "arn:aws:iam::123456789012:role/stem-cogent/sc-normalization-worker-staging-task"
    classification-worker = "arn:aws:iam::123456789012:role/stem-cogent/sc-classification-worker-staging-task"
    enrichment-worker     = "arn:aws:iam::123456789012:role/stem-cogent/sc-enrichment-worker-staging-task"
    clustering-worker     = "arn:aws:iam::123456789012:role/stem-cogent/sc-clustering-worker-staging-task"
    synthesis-worker      = "arn:aws:iam::123456789012:role/stem-cogent/sc-synthesis-worker-staging-task"
  }

  execution_role_arns = {
    api-service           = "arn:aws:iam::123456789012:role/stem-cogent/sc-api-service-staging-execution"
    frontend-service      = "arn:aws:iam::123456789012:role/stem-cogent/sc-frontend-service-staging-execution"
    scheduler-worker      = "arn:aws:iam::123456789012:role/stem-cogent/sc-scheduler-worker-staging-execution"
    collector-worker      = "arn:aws:iam::123456789012:role/stem-cogent/sc-collector-worker-staging-execution"
    validation-worker     = "arn:aws:iam::123456789012:role/stem-cogent/sc-validation-worker-staging-execution"
    normalization-worker  = "arn:aws:iam::123456789012:role/stem-cogent/sc-normalization-worker-staging-execution"
    classification-worker = "arn:aws:iam::123456789012:role/stem-cogent/sc-classification-worker-staging-execution"
    enrichment-worker     = "arn:aws:iam::123456789012:role/stem-cogent/sc-enrichment-worker-staging-execution"
    clustering-worker     = "arn:aws:iam::123456789012:role/stem-cogent/sc-clustering-worker-staging-execution"
    synthesis-worker      = "arn:aws:iam::123456789012:role/stem-cogent/sc-synthesis-worker-staging-execution"
  }

  api_environment_variables = {
    DATABASE_HOST                = "database.internal"
    DATABASE_NAME                = "stemcogent"
    DATABASE_CREDENTIALS_ARN     = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:database"
    REDIS_HOST                   = "redis.internal"
    REDIS_AUTH_TOKEN_ARN         = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:redis"
    SQS_INGESTION_PRIORITY_URL   = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-ingestion-priority-queue-staging"
    SQS_INGESTION_STANDARD_URL   = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-ingestion-standard-queue-staging"
    SQS_PIPELINE_RAW_SIGNALS_URL = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-pipeline-raw-signals-queue-staging"
    SQS_PIPELINE_VALIDATED_URL   = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-pipeline-validated-queue-staging"
    SQS_PIPELINE_NORMALIZED_URL  = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-pipeline-normalized-queue-staging"
    SQS_PIPELINE_CLASSIFIED_URL  = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-pipeline-classified-queue-staging"
    SQS_PIPELINE_SCORED_URL      = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-pipeline-scored-queue-staging"
    SQS_PIPELINE_CLUSTERED_URL   = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-pipeline-clustered-queue-staging"
    SQS_PIPELINE_SYNTHESIZED_URL = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-pipeline-synthesized-queue-staging"
    SQS_PIPELINE_RECOMMENDED_URL = "https://sqs.eu-west-1.amazonaws.com/123456789012/sc-pipeline-recommended-queue-staging"
  }
}

run "preserves_staging_replay_pause" {
  command = plan
  variables {
    phase_two_worker_desired_counts = {
      scheduler      = 1, collector = 1, validation = 1, normalization = 1,
      classification = 1, enrichment = 1, clustering = 0, synthesis = 1
    }
  }
  assert {
    condition     = aws_ecs_service.phase_two_worker["clustering"].desired_count == 0
    error_message = "Staging replay must remain paused until explicitly restored."
  }
}

run "rejects_production_worker_pause" {
  command = plan
  variables {
    environment = "prod"
    phase_two_worker_desired_counts = {
      scheduler      = 1, collector = 1, validation = 1, normalization = 1,
      classification = 1, enrichment = 1, clustering = 0, synthesis = 1
    }
  }
  expect_failures = [var.phase_two_worker_desired_counts]
}

run "creates_observable_fargate_cluster" {
  command = plan

  assert {
    condition     = aws_ecs_cluster.this.name == "sc-cluster-staging"
    error_message = "The cluster must use the canonical sc-cluster-{env} name."
  }

  assert {
    condition     = one([for setting in aws_ecs_cluster.this.setting : setting.value if setting.name == "containerInsights"]) == "enabled"
    error_message = "CloudWatch Container Insights must be enabled."
  }

  assert {
    condition = toset(aws_ecs_cluster_capacity_providers.this.capacity_providers) == toset([
      "FARGATE",
      "FARGATE_SPOT",
    ])
    error_message = "The cluster must register both Fargate capacity providers."
  }

  assert {
    condition     = one(aws_ecs_cluster_capacity_providers.this.default_capacity_provider_strategy).capacity_provider == "FARGATE"
    error_message = "The default capacity provider must be on-demand Fargate."
  }
}

run "creates_phase_one_and_core_phase_two_services" {
  command = plan

  assert {
    condition = toset([
      aws_ecs_service.api.name,
      aws_ecs_service.frontend.name,
      aws_ecs_service.phase_two_worker["scheduler"].name,
      aws_ecs_service.phase_two_worker["collector"].name,
      aws_ecs_service.phase_two_worker["validation"].name,
      aws_ecs_service.phase_two_worker["normalization"].name,
      aws_ecs_service.phase_two_worker["classification"].name,
      aws_ecs_service.phase_two_worker["enrichment"].name,
      aws_ecs_service.phase_two_worker["clustering"].name,
      aws_ecs_service.phase_two_worker["synthesis"].name,
      ]) == toset([
      "sc-api-service-staging",
      "sc-frontend-staging",
      "sc-scheduler-worker-staging",
      "sc-collector-worker-staging",
      "sc-validation-worker-staging",
      "sc-normalization-worker-staging",
      "sc-classification-worker-staging",
      "sc-enrichment-worker-staging",
      "sc-clustering-worker-staging",
      "sc-synthesis-worker-staging",
    ])
    error_message = "ECS must create Phase 1 plus the four consolidated core ingestion services."
  }

  assert {
    condition = alltrue([
      for service in [aws_ecs_service.api, aws_ecs_service.frontend] :
      service.deployment_minimum_healthy_percent == (service.desired_count <= 1 ? 0 : 50) &&
      service.deployment_maximum_percent == 100 &&
      one(service.deployment_circuit_breaker).enable &&
      one(service.deployment_circuit_breaker).rollback
    ])
    error_message = "Both services must use the required rolling percentages and circuit-breaker rollback."
  }

  assert {
    condition = alltrue([
      for service in values(aws_ecs_service.phase_two_worker) :
      service.deployment_minimum_healthy_percent == (service.desired_count <= 1 ? 0 : 50) &&
      service.deployment_maximum_percent == 100 &&
      one(service.deployment_circuit_breaker).enable &&
      one(service.deployment_circuit_breaker).rollback &&
      !one(service.network_configuration).assign_public_ip
    ])
    error_message = "Phase 2 workers must be private and use circuit-breaker rollback."
  }

  assert {
    condition = alltrue([
      for service in [aws_ecs_service.api, aws_ecs_service.frontend] :
      !one(service.network_configuration).assign_public_ip &&
      length(one(service.network_configuration).subnets) == 2
    ])
    error_message = "Phase 1 services must run without public IPs across both private-app subnets."
  }
}

run "uses_immutable_images_and_hardened_task_definitions" {
  command = plan

  assert {
    condition = alltrue([
      for definition in [
        jsondecode(aws_ecs_task_definition.api.container_definitions)[0],
        jsondecode(aws_ecs_task_definition.frontend.container_definitions)[0],
        jsondecode(aws_ecs_task_definition.migration.container_definitions)[0],
      ] : endswith(definition.image, ":0123456789abcdef0123456789abcdef01234567") && definition.readonlyRootFilesystem
    ])
    error_message = "Every Phase 1 task must use the immutable bootstrap SHA and a read-only root filesystem."
  }

  assert {
    condition     = aws_ecs_task_definition.migration.family == "sc-migration-task-staging"
    error_message = "The one-shot migration family must match the Application CD contract."
  }

  assert {
    condition = alltrue([
      one([for item in jsondecode(aws_ecs_task_definition.api.container_definitions)[0].environment : item.value if item.name == "TMPDIR"]) == "/dev/shm",
      one([for item in jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].environment : item.value if item.name == "TMPDIR"]) == "/dev/shm",
      one([for item in jsondecode(aws_ecs_task_definition.frontend.container_definitions)[0].environment : item.value if item.name == "HOSTNAME"]) == "0.0.0.0",
    ])
    error_message = "Read-only Phase 1 containers must explicitly use their writable mount and bind address."
  }

  assert {
    condition = alltrue([
      jsondecode(aws_ecs_task_definition.api.container_definitions)[0].logConfiguration.options["awslogs-group"] == "/sc/api-service/staging",
      jsondecode(aws_ecs_task_definition.frontend.container_definitions)[0].logConfiguration.options["awslogs-group"] == "/sc/infrastructure/staging",
      jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].logConfiguration.options["awslogs-group"] == "/sc/api-service/staging",
    ])
    error_message = "Phase 1 tasks must use the observability-owned API and infrastructure log groups."
  }

  assert {
    condition     = jsondecode(aws_ecs_task_definition.frontend.container_definitions)[0].healthCheck.command[0] == "CMD"
    error_message = "The frontend health check must use an ECS command probe."
  }

  assert {
    condition = alltrue([
      length(jsondecode(aws_ecs_task_definition.api.container_definitions)) == 2,
      jsondecode(aws_ecs_task_definition.api.container_definitions)[1].name == "xray-daemon",
      jsondecode(aws_ecs_task_definition.api.container_definitions)[1].readonlyRootFilesystem,
      jsondecode(aws_ecs_task_definition.api.container_definitions)[1].logConfiguration.options["awslogs-stream-prefix"] == "api-service",
      one([for item in jsondecode(aws_ecs_task_definition.api.container_definitions)[0].environment : item.value if item.name == "XRAY_ENABLED"]) == "true",
    ])
    error_message = "The API task must run the hardened X-Ray daemon sidecar with application tracing enabled."
  }

  assert {
    condition = alltrue([
      for key, definition in aws_ecs_task_definition.phase_two_worker :
      endswith(jsondecode(definition.container_definitions)[0].image, ":0123456789abcdef0123456789abcdef01234567") &&
      jsondecode(definition.container_definitions)[0].readonlyRootFilesystem &&
      one([for item in jsondecode(definition.container_definitions)[0].environment : item.value if item.name == "TMPDIR"]) == "/dev/shm" &&
      one([for item in jsondecode(definition.container_definitions)[0].environment : item.value if item.name == "SERVICE_NAME"]) == "sc-${key}-worker-staging"
    ])
    error_message = "Phase 2 worker tasks must use immutable images, read-only roots, writable temp space, and exact service identity."
  }

  assert {
    condition = alltrue([
      jsondecode(aws_ecs_task_definition.phase_two_worker["classification"].container_definitions)[0].logConfiguration.options["awslogs-group"] == "/sc/pipeline/processing/staging",
      jsondecode(aws_ecs_task_definition.phase_two_worker["enrichment"].container_definitions)[0].logConfiguration.options["awslogs-group"] == "/sc/pipeline/processing/staging",
      jsondecode(aws_ecs_task_definition.phase_two_worker["clustering"].container_definitions)[0].logConfiguration.options["awslogs-group"] == "/sc/pipeline/processing/staging",
      jsondecode(aws_ecs_task_definition.phase_two_worker["synthesis"].container_definitions)[0].logConfiguration.options["awslogs-group"] == "/sc/pipeline/synthesis/staging",
    ])
    error_message = "Phase 3 workers must write to the log groups allowed by their execution roles."
  }

}

run "exports_application_cd_contract" {
  command = plan

  assert {
    condition = jsondecode(output.service_deployments_json) == [
      {
        service   = "sc-api-service-staging"
        container = "api"
        image     = "api"
      },
      {
        service   = "sc-frontend-staging"
        container = "frontend"
        image     = "frontend"
      },
      {
        service   = "sc-scheduler-worker-staging"
        container = "scheduler-worker"
        image     = "worker"
      },
      {
        service   = "sc-collector-worker-staging"
        container = "collector-worker"
        image     = "worker"
      },
      {
        service   = "sc-validation-worker-staging"
        container = "validation-worker"
        image     = "worker"
      },
      {
        service   = "sc-normalization-worker-staging"
        container = "normalization-worker"
        image     = "worker"
      },
      {
        service   = "sc-classification-worker-staging"
        container = "classification-worker"
        image     = "worker"
      },
      {
        service   = "sc-enrichment-worker-staging"
        container = "enrichment-worker"
        image     = "worker"
      },
      {
        service   = "sc-clustering-worker-staging"
        container = "clustering-worker"
        image     = "worker"
      },
      {
        service   = "sc-synthesis-worker-staging"
        container = "synthesis-worker"
        image     = "worker"
      },
    ]
    error_message = "ECS_SERVICE_DEPLOYMENTS must describe all Phase 1 through Phase 3 containers."
  }
}
