output "log_ids" {
  description = "Function invocation log OCIDs keyed by log_params key."
  value       = { for name, log in oci_logging_log.invoke : name => log.id }
}
