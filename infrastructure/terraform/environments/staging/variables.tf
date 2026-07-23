variable "aws_region" {
  description = "AWS region in which Stem Cogent resources are deployed."
  type        = string
  default     = "eu-west-1"
}

variable "environment" {
  description = "Stem Cogent deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "expected_account_id" {
  description = "AWS account that this environment is permitted to target."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "expected_account_id must be a 12-digit AWS account ID."
  }
}

variable "project_name" {
  description = "Project tag applied to all supported AWS resources."
  type        = string
  default     = "stem-cogent"
}
