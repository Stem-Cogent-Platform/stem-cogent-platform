variable "environment" {
  description = "Stem Cogent deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to ECR repository tags."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used in ECR repository names."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "kms_key_arn" {
  description = "Optional customer-managed KMS key ARN. Null uses the AWS-managed Amazon ECR KMS key."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.kms_key_arn == null || can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/.+$", var.kms_key_arn))
    error_message = "kms_key_arn must be null or a valid KMS key ARN."
  }
}

variable "tagged_image_retention_count" {
  description = "Number of immutable tagged releases retained per repository."
  type        = number
  default     = 50

  validation {
    condition     = var.tagged_image_retention_count >= 10 && var.tagged_image_retention_count <= 1000 && floor(var.tagged_image_retention_count) == var.tagged_image_retention_count
    error_message = "tagged_image_retention_count must be a whole number between 10 and 1000."
  }
}

variable "untagged_image_retention_days" {
  description = "Number of days untagged image layers are retained."
  type        = number
  default     = 7

  validation {
    condition     = var.untagged_image_retention_days >= 1 && var.untagged_image_retention_days <= 30 && floor(var.untagged_image_retention_days) == var.untagged_image_retention_days
    error_message = "untagged_image_retention_days must be a whole number between 1 and 30."
  }
}

variable "tags" {
  description = "Additional tags to merge onto every ECR repository."
  type        = map(string)
  default     = {}
}
