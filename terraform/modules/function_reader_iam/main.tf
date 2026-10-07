resource "oci_identity_dynamic_group" "function" {
  for_each = var.reader_params

  compartment_id = var.tenancy_id
  name           = each.value.dynamic_group_name
  description    = "Read OCI limits from Function ${each.key}"
  matching_rule  = "ALL {resource.type='fnfunc', resource.id='${each.value.function_id}'}"
}

resource "oci_identity_policy" "read_limits" {
  for_each = var.reader_params

  compartment_id = var.tenancy_id
  name           = each.value.policy_name
  description    = "Read service limits and resource availability for Function ${each.key}"
  statements = [
    "Allow dynamic-group ${oci_identity_dynamic_group.function[each.key].name} to inspect resource-availability in tenancy",
    "Allow dynamic-group ${oci_identity_dynamic_group.function[each.key].name} to read resource-availability in tenancy",
    "Allow dynamic-group ${oci_identity_dynamic_group.function[each.key].name} to inspect compartments in tenancy",
    "Allow dynamic-group ${oci_identity_dynamic_group.function[each.key].name} to inspect policies in tenancy",
    "Allow dynamic-group ${oci_identity_dynamic_group.function[each.key].name} to use metrics in compartment id ${each.value.metric_compartment_id} where target.metrics.namespace = 'limit_warnings'",
  ]
}
