variable "app_params" {
  description = "OCI Functions applications, keyed by a stable name."
  type = map(object({
    compartment_id             = string
    display_name               = string
    subnet_ids                 = list(string)
    network_security_group_ids = optional(list(string), [])
    shape                      = optional(string, "GENERIC_X86")
  }))

  validation {
    condition     = alltrue([for app in values(var.app_params) : length(app.subnet_ids) > 0])
    error_message = "Each Functions application requires at least one subnet OCID."
  }
}
