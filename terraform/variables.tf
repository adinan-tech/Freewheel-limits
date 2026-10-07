variable "region" {
  description = "Region where the Function and Resource Scheduler run."
  type        = string
}

variable "home_region" {
  description = "Tenancy home region for IAM dynamic groups and policies."
  type        = string
}

variable "tenancy_id" {
  description = "Tenancy OCID for limit API calls and IAM policies."
  type        = string
}

variable "function_compartment_id" {
  description = "Compartment OCID for the Function application and invocation logs."
  type        = string
}

variable "archive_bucket_name" {
  description = "Existing private Object Storage bucket name in this tenancy and region; null creates a dedicated bucket."
  type        = string
  default     = null

  validation {
    condition     = var.archive_bucket_name == null ? true : length(trimspace(var.archive_bucket_name)) > 0
    error_message = "archive_bucket_name must be null or a non-empty bucket name."
  }
}

variable "subnet_id" {
  description = "Existing subnet OCID with access to OCI APIs."
  type        = string

  validation {
    condition     = startswith(var.subnet_id, "ocid1.subnet.")
    error_message = "Provide one existing subnet OCID."
  }
}

variable "function_id" {
  description = "Internal deploy_stack.py value for the code-only Function OCID; customers do not set it."
  type        = string
  default     = null

  validation {
    condition     = var.function_id == null || startswith(var.function_id, "ocid1.fnfunc.")
    error_message = "function_id must be an OCI Function OCID."
  }
}

variable "schedule_start_utc" {
  description = "Future RFC 3339 start time, leaving time for IAM policy propagation."
  type        = string
}

variable "check_schedule_utc" {
  description = "Five-field UTC cron expression; Resource Scheduler supports one-hour minimum interval."
  type        = string
}

variable "email_recipients" {
  description = "Recipients reserved for A4 Notifications subscriptions."
  type        = list(string)
}

variable "monitors" {
  description = "Named service limits selected for warning checks."
  type = map(object({
    service_name        = string
    limit_name          = string
    availability_domain = optional(string)
    warning_percent     = number
  }))

  validation {
    condition = length(var.monitors) > 0 && alltrue([
      for monitor in values(var.monitors) : monitor.warning_percent >= 0 && monitor.warning_percent < 100
    ])
    error_message = "Provide at least one monitor with warning_percent between 0 (inclusive) and 100."
  }

}

variable "name_prefix" {
  description = "Stable prefix for created resources."
  type        = string
  default     = "limit_warnings"
}
