# Scheduled Functions module

Creates one OCI Resource Scheduler schedule per map entry, plus a dynamic group and policy so that schedule can invoke only its selected Function. It follows Thunder's `for_each`/parameter-map module pattern. The Function itself is created elsewhere.

```hcl
module "scheduled_limit_checker" {
  source     = "./modules/scheduled_functions"
  tenancy_id = var.tenancy_id
  providers = {
    oci      = oci
    oci.home = oci.home
  }

  schedule_params = {
    pilot = {
      display_name            = "limit-checker-pilot"
      description             = "Check selected OCI service limits"
      schedule_compartment_id = var.schedule_compartment_id
      function_compartment_id = var.function_compartment_id
      function_id             = var.function_id
      recurrence_type         = "CRON"
      recurrence_details      = "0 * * * *" # hourly, UTC
      time_starts             = var.schedule_start_utc # RFC 3339, future time
      dynamic_group_name      = "limit_checker_schedule"
      policy_name             = "limit_checker_schedule_invoke"
    }
  }
}
```

The default provider creates the schedule in the Function's region; `oci.home` creates IAM resources in the tenancy home region. `function_id` is supplied after ZIP deployment. Resource Scheduler runs at UTC times and has a one-hour minimum interval. OCI IAM changes may take time to propagate before the first scheduled run. The Terraform identity used to apply this module needs permission to create schedules, dynamic groups, and policies. Function runtime permissions for reading limits belong to the Function's own dynamic group and are outside this module.

Validate the final policy in the pilot tenancy because Oracle's schedule tutorial shows a broader example policy.
