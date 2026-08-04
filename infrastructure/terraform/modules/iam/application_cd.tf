locals {
  github_oidc_provider_arn = "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:oidc-provider/token.actions.githubusercontent.com"
  ecs_cluster_arn = coalesce(
    var.ecs_cluster_arn,
    "arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${var.aws_account_id}:cluster/${var.resource_prefix}-cluster-${var.environment}",
  )
  github_oidc_subject = coalesce(
    var.github_oidc_subject_override,
    "repo:${var.github_repository}:environment:${var.github_environment_name}",
  )

  application_cd_service_names = toset([
    "${var.resource_prefix}-api-service-${var.environment}",
    "${var.resource_prefix}-frontend-${var.environment}",
  ])
  application_cd_task_definition_families = toset([
    "${var.resource_prefix}-api-service-${var.environment}",
    "${var.resource_prefix}-frontend-${var.environment}",
    "${var.resource_prefix}-migration-task-${var.environment}",
  ])
  application_cd_service_arns = toset([
    for service_name in local.application_cd_service_names :
    "${replace(local.ecs_cluster_arn, ":cluster/", ":service/")}/${service_name}"
  ])
  application_cd_task_definition_arns = toset([
    for family in local.application_cd_task_definition_families :
    "arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${var.aws_account_id}:task-definition/${family}:*"
  ])
  application_cd_pass_role_arns = toset([
    aws_iam_role.task["api-service"].arn,
    aws_iam_role.execution["api-service"].arn,
    aws_iam_role.task["frontend-service"].arn,
    aws_iam_role.execution["frontend-service"].arn,
  ])

  github_actions_trust_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "GitHubApplicationCDOnly"
        Effect = "Allow"
        Principal = {
          Federated = local.github_oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud"                 = "sts.amazonaws.com"
            "token.actions.githubusercontent.com:sub"                 = local.github_oidc_subject
            "token.actions.githubusercontent.com:repository"          = var.github_repository
            "token.actions.githubusercontent.com:repository_id"       = var.github_repository_id
            "token.actions.githubusercontent.com:repository_owner_id" = var.github_repository_owner_id
            "token.actions.githubusercontent.com:environment"         = var.github_environment_name
            "token.actions.githubusercontent.com:ref"                 = var.github_deployment_ref
            "token.actions.githubusercontent.com:workflow"            = "Application CD"
          }
        }
      },
    ]
  })

  application_build_policy_statements = [
    {
      Sid      = "AuthenticateToEcr"
      Effect   = "Allow"
      Action   = ["ecr:GetAuthorizationToken"]
      Resource = ["*"]
    },
    {
      Sid    = "DescribeApplicationRepositories"
      Effect = "Allow"
      Action = [
        "ecr:DescribeRepositories",
      ]
      Resource = sort(values(var.ecr_repository_arns))
    },
    {
      Sid    = "PushApplicationImages"
      Effect = "Allow"
      Action = [
        "ecr:BatchCheckLayerAvailability",
        "ecr:CompleteLayerUpload",
        "ecr:InitiateLayerUpload",
        "ecr:PutImage",
        "ecr:UploadLayerPart",
      ]
      Resource = sort(values(var.ecr_repository_arns))
    },
  ]

  application_deploy_policy_statements = [
    {
      Sid      = "DescribeDeploymentCluster"
      Effect   = "Allow"
      Action   = ["ecs:DescribeClusters"]
      Resource = [local.ecs_cluster_arn]
    },
    {
      Sid    = "ReadAndUpdatePhaseOneServices"
      Effect = "Allow"
      Action = [
        "ecs:DescribeServices",
        "ecs:UpdateService",
      ]
      Resource = sort(tolist(local.application_cd_service_arns))
      Condition = {
        ArnEquals = {
          "ecs:cluster" = local.ecs_cluster_arn
        }
      }
    },
    {
      Sid      = "DescribeTaskDefinitions"
      Effect   = "Allow"
      Action   = ["ecs:DescribeTaskDefinition"]
      Resource = ["*"]
    },
    {
      Sid      = "RegisterPhaseOneTaskDefinitions"
      Effect   = "Allow"
      Action   = ["ecs:RegisterTaskDefinition"]
      Resource = sort(tolist(local.application_cd_task_definition_arns))
    },
    {
      Sid      = "RunMigrationTask"
      Effect   = "Allow"
      Action   = ["ecs:RunTask"]
      Resource = ["arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${var.aws_account_id}:task-definition/${var.resource_prefix}-migration-task-${var.environment}:*"]
      Condition = {
        ArnEquals = {
          "ecs:cluster" = local.ecs_cluster_arn
        }
      }
    },
    {
      Sid      = "DescribeMigrationTasks"
      Effect   = "Allow"
      Action   = ["ecs:DescribeTasks"]
      Resource = ["${replace(local.ecs_cluster_arn, ":cluster/", ":task/")}/*"]
      Condition = {
        ArnEquals = {
          "ecs:cluster" = local.ecs_cluster_arn
        }
      }
    },
    {
      Sid      = "PassOnlyPhaseOneTaskRoles"
      Effect   = "Allow"
      Action   = ["iam:PassRole"]
      Resource = sort(tolist(local.application_cd_pass_role_arns))
      Condition = {
        StringEquals = {
          "iam:PassedToService" = "ecs-tasks.amazonaws.com"
        }
      }
    },
  ]

  application_build_actions = flatten([
    for statement in local.application_build_policy_statements : statement.Action
  ])
  application_deploy_actions = flatten([
    for statement in local.application_deploy_policy_statements : statement.Action
  ])
}

check "application_cd_repository_contract" {
  assert {
    condition     = toset(keys(var.ecr_repository_arns)) == toset(["api", "worker", "frontend"])
    error_message = "Application CD requires exactly the api, worker, and frontend ECR repositories."
  }
}

check "application_cd_role_separation" {
  assert {
    condition     = alltrue([for action in local.application_build_actions : !startswith(action, "ecs:")])
    error_message = "The Application CD build role must not receive ECS permissions."
  }

  assert {
    condition     = alltrue([for action in local.application_deploy_actions : !startswith(action, "ecr:")])
    error_message = "The Application CD deploy role must not receive ECR permissions."
  }

  assert {
    condition = alltrue(concat(
      [for action in local.application_build_actions : !strcontains(action, "*")],
      [for action in local.application_deploy_actions : !strcontains(action, "*")],
    ))
    error_message = "Application CD policies must enumerate IAM actions without action wildcards."
  }
}

resource "aws_iam_role" "application_build" {
  name                 = "${var.resource_prefix}-github-application-build-${var.environment}"
  description          = "GitHub OIDC identity that can push Stem Cogent application images in ${var.environment}"
  path                 = var.role_path
  assume_role_policy   = local.github_actions_trust_policy
  max_session_duration = 3600
  permissions_boundary = var.permissions_boundary_arn

  tags = merge(local.common_tags, {
    Name        = "${var.resource_prefix}-github-application-build-${var.environment}"
    RolePurpose = "application-build"
  })
}

resource "aws_iam_role_policy" "application_build" {
  name = "${var.resource_prefix}-application-build-${var.environment}"
  role = aws_iam_role.application_build.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = local.application_build_policy_statements
  })
}

resource "aws_iam_role" "application_deploy" {
  name                 = "${var.resource_prefix}-github-application-deploy-${var.environment}"
  description          = "GitHub OIDC identity that can deploy Stem Cogent ECS workloads in ${var.environment}"
  path                 = var.role_path
  assume_role_policy   = local.github_actions_trust_policy
  max_session_duration = 3600
  permissions_boundary = var.permissions_boundary_arn

  tags = merge(local.common_tags, {
    Name        = "${var.resource_prefix}-github-application-deploy-${var.environment}"
    RolePurpose = "application-deploy"
  })
}

resource "aws_iam_role_policy" "application_deploy" {
  name = "${var.resource_prefix}-application-deploy-${var.environment}"
  role = aws_iam_role.application_deploy.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = local.application_deploy_policy_statements
  })
}
