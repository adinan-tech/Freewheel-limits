resource "oci_resource_scheduler_schedule" "function" {
  for_each = var.schedule_params

  action             = "START_RESOURCE"
  compartment_id     = each.value.schedule_compartment_id
  display_name       = each.value.display_name
  description        = each.value.description
  recurrence_type    = each.value.recurrence_type
  recurrence_details = each.value.recurrence_details
  time_starts        = each.value.time_starts

  resources {
    id = each.value.function_id
  }
}

resource "oci_identity_dynamic_group" "schedule" {
  for_each = var.schedule_params
  provider = oci.home

  compartment_id = var.tenancy_id
  name           = each.value.dynamic_group_name
  description    = "Allows Resource Scheduler ${each.value.display_name} to invoke its Function"
  matching_rule  = "ALL {resource.type='resourceschedule', resource.id='${oci_resource_scheduler_schedule.function[each.key].id}'}"
}

resource "oci_identity_policy" "invoke" {
  for_each = var.schedule_params
  provider = oci.home

  compartment_id = var.tenancy_id
  name           = each.value.policy_name
  description    = "Invoke permission for Resource Scheduler ${each.value.display_name}"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.schedule[each.key].name} to read fn-app in compartment id ${each.value.function_compartment_id}",
    "Allow dynamic-group ${oci_identity_dynamic_group.schedule[each.key].name} to read fn-function in compartment id ${each.value.function_compartment_id}",
    "Allow dynamic-group ${oci_identity_dynamic_group.schedule[each.key].name} to use fn-invocation in compartment id ${each.value.function_compartment_id} where target.function.id = '${each.value.function_id}'",
  ]
}
