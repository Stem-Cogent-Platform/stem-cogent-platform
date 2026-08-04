variable "aws_account_id" {
  description = "AWS account that owns the service roles and application resources."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be a 12-digit AWS account ID."
  }
}

variable "aws_region" {
  description = "AWS region in which regional application resources are deployed."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]$", var.aws_region))
    error_message = "aws_region must be a valid AWS region name."
  }
}

variable "environment" {
  description = "Stem Cogent deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to IAM role tags."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used in IAM role and application resource names."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "queue_arns" {
  description = "SQS queue ARNs keyed by the 17 logical names from SC-DOC-009 Section 6.3."
  type        = map(string)

  validation {
    condition = alltrue([
      for arn in values(var.queue_arns) :
      can(regex("^arn:[^:]+:sqs:[^:]+:[0-9]{12}:[A-Za-z0-9_-]+$", arn))
    ])
    error_message = "Every queue_arns value must be a valid SQS queue ARN."
  }
}

variable "bucket_arns" {
  description = "Application S3 bucket ARNs keyed by the logical purpose exported by the S3 module."
  type        = map(string)

  validation {
    condition = alltrue([
      for arn in values(var.bucket_arns) :
      can(regex("^arn:[^:]+:s3:::[^/]+$", arn))
    ])
    error_message = "Every bucket_arns value must be a valid S3 bucket ARN."
  }
}

variable "bucket_kms_key_arns" {
  description = "KMS key ARN used by each S3 bucket, keyed by the same logical purpose as bucket_arns."
  type        = map(string)

  validation {
    condition = alltrue([
      for arn in values(var.bucket_kms_key_arns) :
      can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/.+$", arn))
    ])
    error_message = "Every bucket_kms_key_arns value must be a valid KMS key ARN."
  }
}

variable "secret_arns" {
  description = "Managed Secrets Manager secret ARNs keyed by application purpose."
  type        = map(string)

  validation {
    condition = alltrue([
      for arn in values(var.secret_arns) :
      can(regex("^arn:[^:]+:secretsmanager:[^:]+:[0-9]{12}:secret:.+$", arn))
    ])
    error_message = "Every secret_arns value must be a valid Secrets Manager ARN."
  }
}

variable "ecr_repository_arns" {
  description = "Canonical ECR repository ARNs keyed by api, worker, and frontend."
  type        = map(string)

  validation {
    condition = toset(keys(var.ecr_repository_arns)) == toset([
      "api",
      "worker",
      "frontend",
      ]) && alltrue([
      for arn in values(var.ecr_repository_arns) :
      can(regex("^arn:[^:]+:ecr:[^:]+:[0-9]{12}:repository/[A-Za-z0-9._/-]+$", arn))
    ])
    error_message = "ecr_repository_arns must contain valid api, worker, and frontend repository ARNs."
  }
}

variable "ecs_cluster_arn" {
  description = "Optional ARN of the environment ECS cluster. Null derives the canonical ARN without creating a module dependency cycle."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.ecs_cluster_arn == null || can(regex("^arn:[^:]+:ecs:[^:]+:[0-9]{12}:cluster/[A-Za-z0-9_-]+$", var.ecs_cluster_arn))
    error_message = "ecs_cluster_arn must be null or a valid ECS cluster ARN."
  }
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the Application CD roles, in owner/name form."
  type        = string
  default     = "Stem-Cogent-Platform/stem-cogent-platform"

  validation {
    condition     = can(regex("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", var.github_repository))
    error_message = "github_repository must use owner/name format."
  }
}

variable "github_repository_id" {
  description = "Immutable numeric GitHub repository ID required in the OIDC token."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_id))
    error_message = "github_repository_id must contain only digits."
  }
}

variable "github_repository_owner_id" {
  description = "Immutable numeric GitHub repository owner ID required in the OIDC token."
  type        = string

  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_owner_id))
    error_message = "github_repository_owner_id must contain only digits."
  }
}

variable "github_environment_name" {
  description = "GitHub Environment attached to Application CD jobs."
  type        = string

  validation {
    condition     = contains(["staging", "production"], var.github_environment_name)
    error_message = "github_environment_name must be staging or production."
  }
}

variable "github_deployment_ref" {
  description = "Exact Git ref allowed to assume the Application CD roles."
  type        = string

  validation {
    condition     = can(regex("^refs/heads/[A-Za-z0-9._/-]+$", var.github_deployment_ref))
    error_message = "github_deployment_ref must be a full refs/heads/... reference."
  }
}

variable "github_oidc_subject_override" {
  description = "Optional exact GitHub OIDC subject, used if the repository opts into immutable/custom subject claims."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.github_oidc_subject_override == null || startswith(var.github_oidc_subject_override, "repo:")
    error_message = "github_oidc_subject_override must be null or an exact GitHub repository subject beginning with repo:."
  }
}

variable "permissions_boundary_arn" {
  description = "Optional IAM permissions boundary applied to every task and execution role."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.permissions_boundary_arn == null || can(regex("^arn:[^:]+:iam::[0-9]{12}:policy/.+$", var.permissions_boundary_arn))
    error_message = "permissions_boundary_arn must be null or a valid IAM policy ARN."
  }
}

variable "role_path" {
  description = "IAM path under which all Stem Cogent ECS roles are created."
  type        = string
  default     = "/stem-cogent/"

  validation {
    condition     = can(regex("^/(|[A-Za-z0-9.,+@=_/-]+/)$", var.role_path))
    error_message = "role_path must be a valid IAM path beginning and ending with a slash."
  }
}

variable "max_session_duration" {
  description = "Maximum task-role session duration in seconds."
  type        = number
  default     = 3600

  validation {
    condition     = var.max_session_duration >= 3600 && var.max_session_duration <= 43200
    error_message = "max_session_duration must be between 3600 and 43200 seconds."
  }
}

variable "tags" {
  description = "Additional tags to merge onto every IAM role."
  type        = map(string)
  default     = {}
}
