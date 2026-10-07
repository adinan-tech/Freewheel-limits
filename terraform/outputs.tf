output "application_id" {
  description = "OCID of the Terraform-managed Functions application."
  value       = module.functions.application_ids["checker"]
}

output "archive_bucket_name" {
  description = "Selected private Object Storage bucket for the Function ZIP."
  value       = local.archive_bucket_name
}

output "archive_bucket_compartment_id" {
  description = "Compartment containing the selected archive bucket."
  value       = local.archive_bucket_compartment_id
}

output "archive_bucket_managed" {
  description = "Whether Terraform creates and manages the archive bucket."
  value       = var.archive_bucket_name == null
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

output "notification_topic_id" {
  description = "OCID of the Notifications topic for limit warnings."
  value       = var.function_id == null ? null : oci_ons_notification_topic.limit_warnings[0].topic_id
}
