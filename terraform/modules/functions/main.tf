resource "oci_functions_application" "app" {
  for_each = var.app_params

  compartment_id             = each.value.compartment_id
  display_name               = each.value.display_name
  subnet_ids                 = each.value.subnet_ids
  network_security_group_ids = each.value.network_security_group_ids
  shape                      = each.value.shape
}
