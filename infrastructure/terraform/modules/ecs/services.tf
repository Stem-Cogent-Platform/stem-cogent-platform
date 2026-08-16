locals {
  api_service_name      = "${var.resource_prefix}-api-service-${var.environment}"
  frontend_service_name = "${var.resource_prefix}-frontend-${var.environment}"
  migration_family      = "${var.resource_prefix}-migration-task-${var.environment}"

  api_container_name       = "api"
  frontend_container_name  = "frontend"
  migration_container_name = "migration"

  runtime_environment_variables = {
    AWS_REGION   = var.aws_region
    ENVIRONMENT  = var.environment
    LOG_LEVEL    = "INFO"
    SERVICE_NAME = local.api_service_name
    TMPDIR       = "/dev/shm"
  }

  api_environment_variables = merge(var.api_environment_variables, local.runtime_environment_variables, {
    AWS_XRAY_DAEMON_ADDRESS = "127.0.0.1:2000"
    XRAY_ENABLED            = "true"
  })

  migration_environment_variables = merge(var.api_environment_variables, local.runtime_environment_variables, {
    SERVICE_NAME = local.migration_family
    XRAY_ENABLED = "false"
  })

  bootstrap_images = {
    api      = "${var.ecr_repository_urls["api"]}:${var.bootstrap_image_tag}"
    frontend = "${var.ecr_repository_urls["frontend"]}:${var.bootstrap_image_tag}"
  }

  service_deployments = [
    {
      service   = local.api_service_name
      container = local.api_container_name
      image     = "api"
    },
    {
      service   = local.frontend_service_name
      container = local.frontend_container_name
      image     = "frontend"
    },
  ]
}

resource "aws_ecs_task_definition" "api" {
  family                   = local.api_service_name
  cpu                      = "1024"
  memory                   = "2048"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  task_role_arn            = var.task_role_arns["api-service"]
  execution_role_arn       = var.execution_role_arns["api-service"]

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  volume {
    name = "tmp"
  }

  container_definitions = jsonencode([
    {
      name                   = local.api_container_name
      image                  = local.bootstrap_images.api
      essential              = true
      readonlyRootFilesystem = true
      user                   = "1000"
      stopTimeout            = 30

      portMappings = [{
        name          = "http"
        containerPort = 8000
        hostPort      = 8000
        protocol      = "tcp"
        appProtocol   = "http"
      }]

      environment = [
        for name in sort(keys(local.api_environment_variables)) : {
          name  = name
          value = local.api_environment_variables[name]
        }
      ]

      healthCheck = {
        command = [
          "CMD",
          "python",
          "-c",
          "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=5).close()",
        ]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 60
      }

      linuxParameters = {
        initProcessEnabled = true
      }

      mountPoints = [{
        sourceVolume  = "tmp"
        containerPath = "/tmp"
        readOnly      = false
      }]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.phase_one_log_group_names["api"]
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api-service"
        }
      }
    },
    {
      name                   = "xray-daemon"
      image                  = "public.ecr.aws/xray/aws-xray-daemon:3.x"
      essential              = true
      cpu                    = 32
      memoryReservation      = 256
      readonlyRootFilesystem = true

      command = [
        "-t", "0.0.0.0:2000",
        "-b", "0.0.0.0:2000",
      ]

      portMappings = [
        {
          containerPort = 2000
          hostPort      = 2000
          protocol      = "udp"
        },
        {
          containerPort = 2000
          hostPort      = 2000
          protocol      = "tcp"
        },
      ]

      environment = [{
        name  = "AWS_REGION"
        value = var.aws_region
      }]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.phase_one_log_group_names["api"]
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api-service"
        }
      }
    },
  ])

  tags = merge(local.common_tags, {
    Name    = local.api_service_name
    Service = "api"
  })
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = local.frontend_service_name
  cpu                      = "512"
  memory                   = "1024"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  task_role_arn            = var.task_role_arns["frontend-service"]
  execution_role_arn       = var.execution_role_arns["frontend-service"]

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  volume {
    name = "tmp"
  }

  volume {
    name = "next-cache"
  }

  container_definitions = jsonencode([
    {
      name                   = local.frontend_container_name
      image                  = local.bootstrap_images.frontend
      essential              = true
      readonlyRootFilesystem = true
      user                   = "1001"
      stopTimeout            = 30

      portMappings = [{
        name          = "http"
        containerPort = 3000
        hostPort      = 3000
        protocol      = "tcp"
        appProtocol   = "http"
      }]

      environment = [
        {
          name  = "HOSTNAME"
          value = "0.0.0.0"
        },
        {
          name  = "NODE_ENV"
          value = "production"
        },
        {
          name  = "PORT"
          value = "3000"
        },
      ]

      healthCheck = {
        command = [
          "CMD",
          "node",
          "-e",
          "require('http').get('http://127.0.0.1:3000/', r => process.exit(r.statusCode < 400 ? 0 : 1)).on('error', () => process.exit(1))",
        ]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 30
      }

      linuxParameters = {
        initProcessEnabled = true
      }

      mountPoints = [
        {
          sourceVolume  = "tmp"
          containerPath = "/tmp"
          readOnly      = false
        },
        {
          sourceVolume  = "next-cache"
          containerPath = "/app/.next/cache"
          readOnly      = false
        },
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.phase_one_log_group_names["infrastructure"]
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "frontend-service"
        }
      }
    },
  ])

  tags = merge(local.common_tags, {
    Name    = local.frontend_service_name
    Service = "frontend"
  })
}

resource "aws_ecs_task_definition" "migration" {
  family                   = local.migration_family
  cpu                      = "512"
  memory                   = "1024"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]

  # Migrations use the same application identity and image as the API. This
  # keeps database access least-privilege and matches the CD pass-role policy.
  task_role_arn      = var.task_role_arns["api-service"]
  execution_role_arn = var.execution_role_arns["api-service"]

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  volume {
    name = "tmp"
  }

  container_definitions = jsonencode([
    {
      name                   = local.migration_container_name
      image                  = local.bootstrap_images.api
      command                = ["alembic", "upgrade", "head"]
      essential              = true
      readonlyRootFilesystem = true
      user                   = "1000"
      stopTimeout            = 120

      environment = [
        for name in sort(keys(local.migration_environment_variables)) : {
          name  = name
          value = local.migration_environment_variables[name]
        }
      ]

      linuxParameters = {
        initProcessEnabled = true
      }

      mountPoints = [{
        sourceVolume  = "tmp"
        containerPath = "/tmp"
        readOnly      = false
      }]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = var.phase_one_log_group_names["api"]
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "api-service"
        }
      }
    },
  ])

  tags = merge(local.common_tags, {
    Name    = local.migration_family
    Service = "migration"
  })
}

resource "aws_ecs_service" "api" {
  name            = local.api_service_name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count

  capacity_provider_strategy {
    base              = 1
    capacity_provider = "FARGATE"
    weight            = 1
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 50
  enable_ecs_managed_tags            = true
  force_new_deployment               = false
  health_check_grace_period_seconds  = 120
  platform_version                   = "LATEST"
  propagate_tags                     = "SERVICE"
  wait_for_steady_state              = true

  deployment_controller {
    type = "ECS"
  }

  network_configuration {
    assign_public_ip = false
    security_groups  = [var.api_security_group_id]
    subnets          = var.private_app_subnet_ids
  }

  load_balancer {
    target_group_arn = var.api_target_group_arn
    container_name   = local.api_container_name
    container_port   = 8000
  }

  lifecycle {
    # Application CD registers immutable revisions and autoscaling will own
    # desired count. Terraform continues to own every other service setting.
    ignore_changes = [task_definition, desired_count]
  }

  tags = merge(local.common_tags, {
    Name    = local.api_service_name
    Service = "api"
  })

  depends_on = [aws_ecs_cluster_capacity_providers.this]
}

resource "aws_ecs_service" "frontend" {
  name            = local.frontend_service_name
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count

  capacity_provider_strategy {
    base              = 1
    capacity_provider = "FARGATE"
    weight            = 1
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 50
  enable_ecs_managed_tags            = true
  force_new_deployment               = false
  health_check_grace_period_seconds  = 120
  platform_version                   = "LATEST"
  propagate_tags                     = "SERVICE"
  wait_for_steady_state              = true

  deployment_controller {
    type = "ECS"
  }

  network_configuration {
    assign_public_ip = false
    security_groups  = [var.frontend_security_group_id]
    subnets          = var.private_app_subnet_ids
  }

  load_balancer {
    target_group_arn = var.frontend_target_group_arn
    container_name   = local.frontend_container_name
    container_port   = 3000
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  tags = merge(local.common_tags, {
    Name    = local.frontend_service_name
    Service = "frontend"
  })

  depends_on = [aws_ecs_cluster_capacity_providers.this]
}
