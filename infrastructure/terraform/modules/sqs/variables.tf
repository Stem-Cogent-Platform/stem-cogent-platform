variable "environment" {
  description = "Stem Cogent deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to SQS tags."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used in SQS queue names."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "queue_visibility_timeouts" {
  description = "Optional visibility timeout overrides, in seconds, keyed by logical queue name."
  type        = map(number)
  default     = {}

  validation {
    condition = alltrue([
      for timeout in values(var.queue_visibility_timeouts) :
      timeout >= 0 && timeout <= 43200 && floor(timeout) == timeout
    ])
    error_message = "Every queue visibility timeout must be a whole number from 0 through 43200 seconds."
  }
}

variable "queue_max_receive_counts" {
  description = "Optional DLQ max receive count overrides keyed by logical queue name."
  type        = map(number)
  default     = {}

  validation {
    condition = alltrue([
      for count in values(var.queue_max_receive_counts) :
      count >= 1 && count <= 1000 && floor(count) == count
    ])
    error_message = "Every max receive count must be a whole number from 1 through 1000."
  }
}

variable "dead_letter_retention_seconds" {
  description = "Retention for failed messages. Defaults to the SQS maximum of 14 days."
  type        = number
  default     = 1209600

  validation {
    condition = (
      var.dead_letter_retention_seconds >= 60 &&
      var.dead_letter_retention_seconds <= 1209600 &&
      floor(var.dead_letter_retention_seconds) == var.dead_letter_retention_seconds
    )
    error_message = "dead_letter_retention_seconds must be a whole number from 60 through 1209600."
  }
}

variable "tags" {
  description = "Additional tags to merge onto every SQS queue."
  type        = map(string)
  default     = {}
}
