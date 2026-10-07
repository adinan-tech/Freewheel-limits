# A3: deploy the limit checker

For the selected Frankfurt `anicolescu` pilot, follow the
[manual A3 walkthrough](PILOT_RUNBOOK.md). The instructions below describe the
reusable deployment flow.

This stack uses Thunder-style Terraform modules for the OCI Functions application, invocation log, Resource Scheduler schedule, optional archive bucket, and least-privilege IAM. The checker itself is a **code-only Python Function** deployed as a ZIP. It needs no Docker image or OCIR repository. Use `deploy_stack.py`: it runs the required internal Terraform stages and OCI CLI deployment as one command.

## Resources created

With an existing private archive bucket, Terraform creates eleven base resources plus one Monitoring alarm per configured monitor:

| Step | Resources |
| --- | --- |
| First apply | Functions application, log group, invocation log, and policy that lets the Functions service read the single checker ZIP. |
| Script | The `limit_warnings_checker` Function. The script is outside Terraform because the provider cannot create a code-only Function. |
| Second internal stage | Function reader dynamic group; policy to read OCI limits and publish metrics; Resource Scheduler schedule; Scheduler dynamic group; policy to invoke the Function; Notifications topic and subscription; one Monitoring alarm per monitor. |

The two IAM dynamic groups are for the Function and Resource Scheduler. The three policies are for ZIP access, limit reads, and Function invocation. If `archive_bucket_name` is empty, Terraform also creates one private Object Storage bucket.

## Email alerts

Terraform creates one Notifications topic, one email subscription per `email_recipients` value, and one Monitoring alarm per monitor. Confirm the email subscription sent by OCI before an alarm can deliver mail. The Function publishes `limit_warnings/LimitUsagePercent`; each alarm fires when that monitor reaches its configured `warning_percent`.

Most monitors use OCI service-limit usage directly. The IAM policy monitor uses `identity/policies-count`; it counts policy objects across the tenancy and its active compartments because OCI does not provide this usage through the standard availability API.

## Pilot monitors

The Frankfurt pilot currently monitors these ten OCI limits. Their warning percentages are set in `terraform/limits.auto.tfvars.json`; the current low values are temporary email-test thresholds and must be restored before handover.

| Monitor key | OCI service / limit | Scope |
| --- | --- | --- |
| `compute_standard3_cores` | Compute / `standard3-core-count` | Availability domain |
| `compute_standard_e4_cores` | Compute / `standard-e4-core-count` | Availability domain |
| `compute_standard_e5_cores` | Compute / `standard-e5-core-count` | Availability domain |
| `compute_custom_images` | Compute / `custom-image-count` | Region |
| `block_volume_count` | Block Storage / `volume-count` | Availability domain |
| `block_total_storage_gb` | Block Storage / `total-storage-gb` | Availability domain |
| `block_backup_count` | Block Storage / `backup-count` | Region |
| `object_bucket_count` | Object Storage / `bucket-count` | Region |
| `load_balancer_flexible_count` | Load Balancer / `lb-flexible-count` | Region |
| `iam_policies_tenancy` | Identity / `policies-count` | Global tenancy; policy objects are counted across active compartments |

## Prerequisites

- An OC1 region that supports code-only Functions, an existing subnet with OCI API access, and permissions to create Functions, schedules, logs, dynamic groups, and policies. Creating a new archive bucket also requires bucket-management access; using an existing bucket requires object-upload access to it.
- Terraform, Python with pip, and OCI CLI **3.94 or newer**, configured for the target tenancy. Credentials stay outside this repository.
- An approved Terraform state backend for customer use. This stack does not create a VCN.

## Deploy

From the repository root:

1. Copy `terraform/limits.example.tfvars.json` to `terraform/limits.auto.tfvars.json`. The example contains the complete ten-monitor template. The copy is the **only file the customer edits**. Values marked `CHANGE HERE` must be replaced; the JSON format does not support inline comments. Every other value is a usable default and can also be changed, including the hourly schedule (`check_schedule_utc`), the warning percentage for each monitor (`warning_percent`), the selected monitor names, and the archive-bucket choice. Set `schedule_start_utc` far enough ahead for deployment and IAM propagation. One stack covers one region. Leave `archive_bucket_name` null to create a private bucket, or set it to an existing private bucket name in the same tenancy and region. The bucket's compartment is discovered automatically. The stack creates a Function archive-read policy scoped to the single ZIP object named `${name_prefix}_checker.zip` in the selected bucket in either case; it never manages or deletes a supplied bucket. A shared existing bucket can contain unrelated objects, which this policy does not grant the Function access to.
2. Run `python -m limit_checker preflight --config terraform/limits.auto.tfvars.json` to validate selected limits against OCI.
3. Run `python scripts/deploy_stack.py apply --config terraform/limits.auto.tfvars.json --profile DEFAULT`.

For a clean recreation, run `python scripts/deploy_stack.py recreate --config terraform/limits.auto.tfvars.json --profile DEFAULT`. It deletes the CLI-managed Function first, removes all Terraform-managed resources, then deploys the full stack. A supplied existing bucket is preserved.

On later code or configuration changes, rerun steps 2 and 3. Allow for IAM propagation before the first scheduled run. Keep `limits.auto.tfvars.json` and Terraform state private and out of Git. Keep the bucket choice stable after deployment; switching between managed and existing buckets needs an explicit migration plan for Terraform state and the Function archive.

## Verify A3

Check the `function_id`, `schedule_id`, and `invocation_log_id` Terraform outputs. After the first scheduled run, inspect invocation logs for one `OK` or `WARNING` result per monitor and confirm tenancy, region, and availability-domain scope. A monitor `ERROR` causes the invocation to fail visibly in logs. Do not mark A3 complete until a live scheduled run succeeds.

The OCI Python SDK makes the archive too large for 25 MB direct upload, so the script uses Object Storage's 250 MB archive limit. Function configuration is limited to 4 KB; a larger monitor set will need external configuration in a later phase. The schedule uses UTC and has a one-hour minimum interval.

References: [Python ZIP layout](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functions-codeonly-python.htm), [creating code-only Functions](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functions-codeonly-creating.htm), [supported runtimes](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/languagessupportedbyfunctions.htm), [Resource Scheduler](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functionsschedulingfunctions-about.htm).
