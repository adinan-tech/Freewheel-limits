output "application_ids" {
  description = "Application OCIDs keyed by app_params key."
  value       = { for name, app in oci_functions_application.app : name => app.id }
}

output "function_ids" {
  description = "Function OCIDs keyed by fn_params key."
  value       = { for name, fn in oci_functions_function.function : name => fn.id }
}
