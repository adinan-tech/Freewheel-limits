resource "oci_functions_application" "app" {
  for_each = var.app_params

  compartment_id             = each.value.compartment_id
  display_name               = each.value.display_name
  subnet_ids                 = each.value.subnet_ids
  network_security_group_ids = each.value.network_security_group_ids
  shape                      = each.value.shape
}

resource "oci_functions_function" "function" {
  for_each = var.fn_params

  application_id                   = oci_functions_application.app[each.value.application_key].id
  display_name                     = each.value.display_name
  image                            = each.value.image
  image_digest                     = each.value.image_digest
  memory_in_mbs                    = each.value.memory_in_mbs
  timeout_in_seconds               = each.value.timeout_in_seconds
  detached_mode_timeout_in_seconds = each.value.detached_timeout_in_seconds
  config                           = each.value.config

  lifecycle {
    precondition {
      condition     = length(jsonencode(each.value.config)) <= 3500
      error_message = "Function environment configuration is too large; OCI permits about 4 KB."
    }
  }
}
