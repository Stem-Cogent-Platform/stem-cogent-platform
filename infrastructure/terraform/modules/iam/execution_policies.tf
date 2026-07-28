locals {
  # Task 1.3.12 defines exactly three image repositories. The backend workers
  # and MLflow use the common worker image repository; each service still has
  # a dedicated execution identity.
  ecr_repository_names = {
    for service in local.services :
    service => service == "api-service" ? "${var.resource_prefix}-api-service-${var.environment}" : service == "frontend-service" ? "${var.resource_prefix}-frontend-${var.environment}" : "${var.resource_prefix}-worker-${var.environment}"
  }

  ecr_repository_arns = {
    for service, repository_name in local.ecr_repository_names :
    service => "arn:${data.aws_partition.current.partition}:ecr:${var.aws_region}:${var.aws_account_id}:repository/${repository_name}"
  }

  # Canonical groups are defined by SC-DOC-009 Section 7.2. Services that
  # share a group are isolated to their own deterministic log-stream prefix.
  log_group_paths = {
    api-service             = "/${var.resource_prefix}/api-service/${var.environment}"
    frontend-service        = "/${var.resource_prefix}/infrastructure/${var.environment}"
    rss-collector-worker    = "/${var.resource_prefix}/pipeline/ingestion/${var.environment}"
    api-collector-worker    = "/${var.resource_prefix}/pipeline/ingestion/${var.environment}"
    scraper-worker          = "/${var.resource_prefix}/pipeline/ingestion/${var.environment}"
    pdf-collector-worker    = "/${var.resource_prefix}/pipeline/ingestion/${var.environment}"
    upload-collector-worker = "/${var.resource_prefix}/pipeline/ingestion/${var.environment}"
    validation-worker       = "/${var.resource_prefix}/pipeline/processing/${var.environment}"
    normalization-worker    = "/${var.resource_prefix}/pipeline/processing/${var.environment}"
    classification-worker   = "/${var.resource_prefix}/pipeline/processing/${var.environment}"
    enrichment-worker       = "/${var.resource_prefix}/pipeline/processing/${var.environment}"
    clustering-worker       = "/${var.resource_prefix}/pipeline/processing/${var.environment}"
    synthesis-worker        = "/${var.resource_prefix}/pipeline/synthesis/${var.environment}"
    alert-worker            = "/${var.resource_prefix}/pipeline/delivery/${var.environment}"
    delivery-worker         = "/${var.resource_prefix}/pipeline/delivery/${var.environment}"
    digest-worker           = "/${var.resource_prefix}/pipeline/delivery/${var.environment}"
    mlflow-server           = "/${var.resource_prefix}/infrastructure/${var.environment}"
  }

  log_group_arns = {
    for service, path in local.log_group_paths :
    service => "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${var.aws_account_id}:log-group:${path}"
  }

  execution_policy_statements = {
    for service in local.services :
    service => [
      {
        # ECR GetAuthorizationToken does not support repository-level ARNs.
        Sid      = "AuthenticateToEcr"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = ["*"]
      },
      {
        Sid    = "PullServiceImage"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
        ]
        Resource = [local.ecr_repository_arns[service]]
      },
      {
        Sid    = "WriteServiceLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = ["${local.log_group_arns[service]}:log-stream:${service}/*"]
      },
    ]
  }

  all_execution_policy_actions = flatten([
    for statements in values(local.execution_policy_statements) : flatten([
      for statement in statements : statement.Action
    ])
  ])
}

check "no_wildcard_execution_actions" {
  assert {
    condition     = alltrue([for action in local.all_execution_policy_actions : !strcontains(action, "*")])
    error_message = "ECS execution-role policies must enumerate every action and may not contain wildcard actions."
  }
}

check "complete_execution_resource_map" {
  assert {
    condition     = toset(keys(local.ecr_repository_arns)) == local.services && toset(keys(local.log_group_arns)) == local.services
    error_message = "Every ECS service must map to one of the three canonical ECR repositories and one canonical CloudWatch log group."
  }
}

resource "aws_iam_role_policy" "execution" {
  for_each = local.services

  name = "${var.resource_prefix}-${each.key}-${var.environment}-execution"
  role = aws_iam_role.execution[each.key].id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = local.execution_policy_statements[each.key]
  })
}
