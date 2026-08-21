variable "environment" {
  description = "Deployment environment used in ECS resource names and tags."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to all ECS resource tags."
  type        = string
  default     = "stem-cogent"

  validation {
    condition     = length(trimspace(var.project_name)) > 0
    error_message = "project_name must not be empty."
  }
}

variable "resource_prefix" {
  description = "Short prefix used in AWS resource names."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "tags" {
  description = "Additional tags to merge onto every supported ECS resource."
  type        = map(string)
  default     = {}
}

variable "aws_region" {
  description = "AWS region used by ECS logging and application runtime configuration."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]$", var.aws_region))
    error_message = "aws_region must be a valid AWS region name."
  }
}

variable "bootstrap_image_tag" {
  description = "Immutable 40-character Git commit SHA already present in the Phase 1 ECR repositories."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.bootstrap_image_tag))
    error_message = "bootstrap_image_tag must be the full lowercase 40-character commit SHA pushed by the Application CD bootstrap run."
  }
}

variable "ecr_repository_urls" {
  description = "Canonical ECR repository URLs keyed by api, worker, and frontend."
  type        = map(string)

  validation {
    condition = toset(keys(var.ecr_repository_urls)) == toset([
      "api",
      "worker",
      "frontend",
      ]) && alltrue([
      for url in values(var.ecr_repository_urls) :
      can(regex("^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com/[A-Za-z0-9._/-]+$", url))
    ])
    error_message = "ecr_repository_urls must contain valid api, worker, and frontend repository URLs."
  }
}

variable "private_app_subnet_ids" {
  description = "Private application subnet IDs used by Phase 1 services and one-shot migrations."
  type        = list(string)

  validation {
    condition = (
      length(distinct(var.private_app_subnet_ids)) >= 2 &&
      alltrue([for subnet_id in var.private_app_subnet_ids : can(regex("^subnet-[0-9a-f]+$", subnet_id))])
    )
    error_message = "private_app_subnet_ids must contain at least two distinct valid subnet IDs."
  }
}

variable "api_security_group_id" {
  description = "Security group assigned to API and migration ENIs."
  type        = string

  validation {
    condition     = can(regex("^sg-[0-9a-f]+$", var.api_security_group_id))
    error_message = "api_security_group_id must be a valid security group ID."
  }
}

variable "frontend_security_group_id" {
  description = "Security group assigned to frontend service ENIs."
  type        = string

  validation {
    condition     = can(regex("^sg-[0-9a-f]+$", var.frontend_security_group_id))
    error_message = "frontend_security_group_id must be a valid security group ID."
  }
}

variable "api_target_group_arn" {
  description = "ALB target-group ARN for API tasks."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:elasticloadbalancing:[^:]+:[0-9]{12}:targetgroup/.+$", var.api_target_group_arn))
    error_message = "api_target_group_arn must be a valid ALB target-group ARN."
  }
}

variable "frontend_target_group_arn" {
  description = "ALB target-group ARN for frontend tasks."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:elasticloadbalancing:[^:]+:[0-9]{12}:targetgroup/.+$", var.frontend_target_group_arn))
    error_message = "frontend_target_group_arn must be a valid ALB target-group ARN."
  }
}

variable "task_role_arns" {
  description = "Dedicated application task-role ARNs keyed by ECS service name."
  type        = map(string)

  validation {
    condition = (
      contains(keys(var.task_role_arns), "api-service") &&
      contains(keys(var.task_role_arns), "frontend-service") &&
      contains(keys(var.task_role_arns), "scheduler-worker") &&
      contains(keys(var.task_role_arns), "collector-worker") &&
      contains(keys(var.task_role_arns), "validation-worker") &&
      contains(keys(var.task_role_arns), "normalization-worker") &&
      contains(keys(var.task_role_arns), "classification-worker") &&
      contains(keys(var.task_role_arns), "enrichment-worker") &&
      contains(keys(var.task_role_arns), "clustering-worker") &&
      contains(keys(var.task_role_arns), "synthesis-worker") &&
      alltrue([for arn in values(var.task_role_arns) : can(regex("^arn:[^:]+:iam::[0-9]{12}:role/.+$", arn))])
    )
    error_message = "task_role_arns must contain valid Phase 1 through Phase 3 runtime role ARNs."
  }
}

variable "execution_role_arns" {
  description = "Dedicated ECS agent execution-role ARNs keyed by ECS service name."
  type        = map(string)

  validation {
    condition = (
      contains(keys(var.execution_role_arns), "api-service") &&
      contains(keys(var.execution_role_arns), "frontend-service") &&
      contains(keys(var.execution_role_arns), "scheduler-worker") &&
      contains(keys(var.execution_role_arns), "collector-worker") &&
      contains(keys(var.execution_role_arns), "validation-worker") &&
      contains(keys(var.execution_role_arns), "normalization-worker") &&
      contains(keys(var.execution_role_arns), "classification-worker") &&
      contains(keys(var.execution_role_arns), "enrichment-worker") &&
      contains(keys(var.execution_role_arns), "clustering-worker") &&
      contains(keys(var.execution_role_arns), "synthesis-worker") &&
      alltrue([for arn in values(var.execution_role_arns) : can(regex("^arn:[^:]+:iam::[0-9]{12}:role/.+$", arn))])
    )
    error_message = "execution_role_arns must contain valid Phase 1 through Phase 3 runtime role ARNs."
  }
}

variable "phase_one_log_group_names" {
  description = "Observability-owned CloudWatch log group names used by application task definitions."
  type        = map(string)

  validation {
    condition = (
      contains(keys(var.phase_one_log_group_names), "api") &&
      contains(keys(var.phase_one_log_group_names), "infrastructure") &&
      contains(keys(var.phase_one_log_group_names), "ingestion") &&
      contains(keys(var.phase_one_log_group_names), "processing") &&
      alltrue([for name in values(var.phase_one_log_group_names) : startswith(name, "/")])
    )
    error_message = "phase_one_log_group_names must contain absolute API, infrastructure, ingestion, and processing log group names."
  }
}

variable "api_environment_variables" {
  description = "Non-secret API and migration runtime configuration. Secret values remain behind ARN references."
  type        = map(string)

  validation {
    condition = length(setsubtract(toset([
      "DATABASE_HOST",
      "DATABASE_NAME",
      "DATABASE_CREDENTIALS_ARN",
      "REDIS_HOST",
      "REDIS_AUTH_TOKEN_ARN",
    ]), toset(keys(var.api_environment_variables)))) == 0
    error_message = "api_environment_variables must include database and Redis endpoints plus their secret ARN references."
  }
}

variable "api_desired_count" {
  description = "Number of API tasks maintained before autoscaling is introduced."
  type        = number
  default     = 2

  validation {
    condition     = var.api_desired_count >= 2 && floor(var.api_desired_count) == var.api_desired_count
    error_message = "api_desired_count must be an integer of at least 2 for high availability."
  }
}

variable "frontend_desired_count" {
  description = "Number of frontend tasks maintained before autoscaling is introduced."
  type        = number
  default     = 2

  validation {
    condition     = var.frontend_desired_count >= 2 && floor(var.frontend_desired_count) == var.frontend_desired_count
    error_message = "frontend_desired_count must be an integer of at least 2 for high availability."
  }
}

variable "phase_two_worker_desired_counts" {
  description = "Desired Fargate tasks for each Phase 2 runtime; the scheduler is intentionally singleton."
  type        = map(number)
  default = {
    scheduler      = 1
    collector      = 2
    validation     = 2
    normalization  = 2
    classification = 2
    enrichment     = 2
    clustering     = 2
    synthesis      = 2
  }

  validation {
    condition = (
      toset(keys(var.phase_two_worker_desired_counts)) == toset([
        "scheduler", "collector", "validation", "normalization",
        "classification", "enrichment", "clustering", "synthesis"
      ]) &&
      var.phase_two_worker_desired_counts["scheduler"] == 1 &&
      alltrue([
        for count in values(var.phase_two_worker_desired_counts) :
        count >= 1 && floor(count) == count
      ])
    )
    error_message = "Worker desired counts require exactly one scheduler and at least one integer task for every Phase 2 and Phase 3 worker."
  }
}
