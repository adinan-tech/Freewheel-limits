variable "tenancy_id" {
  description = "Tenancy OCID where dynamic groups and policies are created."
  type        = string
}

variable "reader_params" {
  description = "Function reader identities, keyed by a stable name."
  type = map(object({
    function_id        = string
    dynamic_group_name = string
    policy_name        = string
  }))
}
