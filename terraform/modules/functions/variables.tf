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

variable "fn_params" {
  description = "Image-based Functions, keyed by a stable name."
  type = map(object({
    application_key             = string
    display_name                = string
    image                       = string
    image_digest                = optional(string)
    memory_in_mbs               = optional(number, 256)
    timeout_in_seconds          = optional(number, 120)
    detached_timeout_in_seconds = optional(number, 120)
    config                      = optional(map(string), {})
  }))

}
