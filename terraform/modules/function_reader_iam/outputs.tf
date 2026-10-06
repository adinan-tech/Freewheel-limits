output "dynamic_group_ids" {
  description = "Function reader dynamic group OCIDs keyed by reader_params key."
  value       = { for name, group in oci_identity_dynamic_group.function : name => group.id }
}
