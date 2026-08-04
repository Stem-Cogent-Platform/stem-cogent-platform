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
