resource "oci_logging_log_group" "function" {
  for_each = var.log_params

  compartment_id = each.value.compartment_id
  display_name   = each.value.group_name
  description    = "Logs for ${each.value.application_name}"
}

resource "oci_logging_log" "invoke" {
  for_each = var.log_params

  display_name       = each.value.log_name
  log_group_id       = oci_logging_log_group.function[each.key].id
  log_type           = "SERVICE"
  is_enabled         = true
  retention_duration = each.value.retention_days

  configuration {
    compartment_id = each.value.compartment_id
    source {
      category    = "invoke"
      resource    = each.value.application_id
      service     = "functions"
      source_type = "OCISERVICE"
    }
  }
}
