variable "log_params" {
  description = "Function invocation logs, keyed by a stable name."
  type = map(object({
    compartment_id   = string
    application_id   = string
    application_name = string
    group_name       = string
    log_name         = string
    retention_days   = optional(number, 30)
  }))
}
