variable "environment" {
  description = "Stem Cogent deployment environment used in every secret path."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to Secrets Manager tags."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used at the root of every secret path."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "kms_key_id" {
  description = "Optional customer-managed KMS key ARN for secret encryption. Null uses the AWS managed Secrets Manager key."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition     = var.kms_key_id == null || can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:(key|alias)/.+$", var.kms_key_id))
    error_message = "kms_key_id must be null or a valid KMS key or alias ARN."
  }
}

variable "recovery_window_in_days" {
  description = "Recovery window applied if a managed secret is deleted."
  type        = number
  default     = 30

  validation {
    condition     = var.recovery_window_in_days >= 7 && var.recovery_window_in_days <= 30
    error_message = "recovery_window_in_days must be between 7 and 30."
  }
}

variable "tags" {
  description = "Additional tags to merge onto every secret definition."
  type        = map(string)
  default     = {}
}
