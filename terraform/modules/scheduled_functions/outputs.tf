output "schedule_ids" {
  description = "Resource Scheduler OCIDs keyed by schedule name."
  value       = { for name, schedule in oci_resource_scheduler_schedule.function : name => schedule.id }
}

output "dynamic_group_ids" {
  description = "Scheduler dynamic group OCIDs keyed by schedule name."
  value       = { for name, group in oci_identity_dynamic_group.schedule : name => group.id }
}
