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
  }

  task_role_arns = {
    api-service      = "arn:aws:iam::123456789012:role/stem-cogent/sc-api-service-staging-task"
    frontend-service = "arn:aws:iam::123456789012:role/stem-cogent/sc-frontend-service-staging-task"
  }

  execution_role_arns = {
    api-service      = "arn:aws:iam::123456789012:role/stem-cogent/sc-api-service-staging-execution"
    frontend-service = "arn:aws:iam::123456789012:role/stem-cogent/sc-frontend-service-staging-execution"
  }

  api_environment_variables = {
    DATABASE_HOST            = "database.internal"
    DATABASE_NAME            = "stemcogent"
    DATABASE_CREDENTIALS_ARN = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:database"
    REDIS_HOST               = "redis.internal"
    REDIS_AUTH_TOKEN_ARN     = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:redis"
  }
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

run "creates_only_phase_one_services" {
  command = plan

  assert {
    condition = toset([
      aws_ecs_service.api.name,
      aws_ecs_service.frontend.name,
      ]) == toset([
      "sc-api-service-staging",
      "sc-frontend-staging",
    ])
    error_message = "Task 1.3.15 must create exactly the API and frontend Phase 1 services."
  }

  assert {
    condition = alltrue([
      for service in [aws_ecs_service.api, aws_ecs_service.frontend] :
      service.deployment_minimum_healthy_percent == 50 &&
      service.deployment_maximum_percent == 200 &&
      one(service.deployment_circuit_breaker).enable &&
      one(service.deployment_circuit_breaker).rollback
    ])
    error_message = "Both services must use the required rolling percentages and circuit-breaker rollback."
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
      one([for item in jsondecode(aws_ecs_task_definition.api.container_definitions)[0].environment : item.value if item.name == "XRAY_ENABLED"]) == "true",
    ])
    error_message = "The API task must run the hardened X-Ray daemon sidecar with application tracing enabled."
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
    ]
    error_message = "ECS_SERVICE_DEPLOYMENTS must describe exactly the API and frontend containers."
  }
}
