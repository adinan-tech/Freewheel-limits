output "function_id" {
  description = "OCID of the limit checker Function."
  value       = module.functions.function_ids["checker"]
}

output "schedule_id" {
  description = "OCID of the Resource Scheduler schedule."
  value       = module.scheduled_functions.schedule_ids["checker"]
}

output "invocation_log_id" {
  description = "OCID of the Function invocation log."
  value       = module.function_logging.log_ids["checker"]
}
