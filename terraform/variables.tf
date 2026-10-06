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

variable "subscription_id" {
  description = "Optional OCI subscription OCID when limit values vary by subscription."
  type        = string
  default     = null
}

variable "function_compartment_id" {
  description = "Compartment OCID for the Function application and invocation logs."
  type        = string
}

variable "schedule_compartment_id" {
  description = "Compartment OCID for the Resource Scheduler schedule; defaults to the Function compartment."
  type        = string
  default     = null
}

variable "subnet_ids" {
  description = "Existing subnets with access to OCI APIs and OCIR."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) > 0
    error_message = "Provide at least one existing subnet OCID."
  }
}

variable "network_security_group_ids" {
  description = "Optional network security group OCIDs for the Function application."
  type        = list(string)
  default     = []
}

variable "function_image" {
  description = "Qualified OCIR image name with immutable version tag; build and push before applying Terraform."
  type        = string
}

variable "function_image_digest" {
  description = "Optional sha256 digest to pin the Function image."
  type        = string
  default     = null
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
      for monitor in values(var.monitors) : monitor.warning_percent > 0 && monitor.warning_percent < 100
    ])
    error_message = "Provide at least one monitor with warning_percent between 0 and 100."
  }
}

variable "name_prefix" {
  description = "Stable prefix for created resources."
  type        = string
  default     = "limit_warnings"
}
