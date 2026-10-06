output "application_ids" {
  description = "Application OCIDs keyed by app_params key."
  value       = { for name, app in oci_functions_application.app : name => app.id }
}
