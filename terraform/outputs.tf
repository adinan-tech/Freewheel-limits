output "application_id" {
  description = "OCID of the Terraform-managed Functions application."
  value       = module.functions.application_ids["checker"]
}

output "archive_bucket_name" {
  description = "Dedicated private Object Storage bucket for the Function ZIP."
  value       = oci_objectstorage_bucket.archive.name
}

output "archive_namespace" {
  description = "Object Storage namespace for the Function ZIP."
  value       = data.oci_objectstorage_namespace.current.namespace
}

output "function_id" {
  description = "OCID of the CLI-managed code-only Function after deployment."
  value       = var.function_id
}

output "schedule_id" {
  description = "OCID of the Resource Scheduler schedule."
  value       = var.function_id == null ? null : module.scheduled_functions[0].schedule_ids["checker"]
}

output "invocation_log_id" {
  description = "OCID of the Function invocation log."
  value       = module.function_logging.log_ids["checker"]
}
