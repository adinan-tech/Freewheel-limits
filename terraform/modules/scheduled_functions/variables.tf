variable "tenancy_id" {
  description = "Tenancy OCID, where the schedule dynamic groups and policies are created."
  type        = string
}

variable "schedule_params" {
  description = "Named Function schedules. Function OCIDs can come from the Functions module outputs."
  type = map(object({
    display_name            = string
    description             = string
    schedule_compartment_id = string
    function_compartment_id = string
    function_id             = string
    recurrence_type         = string
    recurrence_details      = string
    time_starts             = string
    dynamic_group_name      = string
    policy_name             = string
  }))

  validation {
    condition = alltrue([
      for schedule in values(var.schedule_params) :
      contains(["CRON", "ICAL"], schedule.recurrence_type)
    ])
    error_message = "recurrence_type must be CRON or ICAL."
  }
}
