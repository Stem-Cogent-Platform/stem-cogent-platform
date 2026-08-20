variable "aws_account_id" {
  description = "AWS account that owns the globally unique S3 buckets."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be a 12-digit AWS account ID."
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
  description = "Project name applied to S3 tags."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used in bucket names."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "kms_key_arns" {
  description = "Customer-managed KMS key ARNs keyed by KMS module purpose."
  type        = map(string)

  validation {
    condition = alltrue([
      for purpose in [
        "audit",
        "backup",
        "enterprise",
        "ml",
        "raw_signals",
      ] : contains(keys(var.kms_key_arns), purpose)
    ])
    error_message = "kms_key_arns must include audit, backup, enterprise, ml, and raw_signals keys."
  }
}

variable "audit_object_lock_mode" {
  description = "Object Lock mode for the five-year audit archive retention."
  type        = string
  default     = "COMPLIANCE"

  validation {
    condition     = contains(["COMPLIANCE", "GOVERNANCE"], var.audit_object_lock_mode)
    error_message = "audit_object_lock_mode must be COMPLIANCE or GOVERNANCE."
  }
}

variable "force_destroy" {
  description = "Whether Terraform may delete non-empty buckets. Keep false outside disposable test fixtures."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags to merge onto every S3 bucket."
  type        = map(string)
  default     = {}
}
