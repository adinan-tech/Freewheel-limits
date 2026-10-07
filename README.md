# OCI service-limit warnings

This package deploys a scheduled OCI Function that checks selected service
limits and sends email when usage reaches a configurable warning percentage.
It does not change OCI hard limits.

## Prerequisites

- Python 3.10 or later
- Terraform 1.3 or later
- OCI CLI 3.94 or later, configured with a profile that can create Functions,
  Logging, Resource Scheduler, Monitoring, Notifications, IAM policies and
  dynamic groups in the target tenancy
- An existing subnet with outbound access to OCI APIs
- An approved Terraform state backend for production use

Install the Python dependency from the repository root:

```bash
python -m pip install -r requirements.txt
```

## Configure

Copy the example file and edit the copy. This is the only configuration file
that the customer needs to edit.

```bash
cp terraform/limits.example.tfvars.json terraform/limits.auto.tfvars.json
```

On Windows PowerShell:

```powershell
Copy-Item terraform/limits.example.tfvars.json terraform/limits.auto.tfvars.json
```

In `terraform/limits.auto.tfvars.json`, replace every value marked `CHANGE
HERE`. The remaining values are usable defaults and may also be changed:

- `archive_bucket_name`: leave `null` to create a private archive bucket, or
  set the name of an existing private bucket in the target region. A supplied
  bucket is never deleted by this stack.
- `check_schedule_utc`: standard five-field UTC cron expression. OCI Resource
  Scheduler has a minimum interval of one hour. For example, `15 * * * *`
  runs once per hour at minute 15.
- `warning_percent`: soft warning threshold for each monitor. It does not
  change the OCI hard limit.
- `monitors`: selected limits, their scopes, and warning thresholds.

Set `schedule_start_utc` to a future UTC time that gives enough time for the
deployment and IAM propagation. Keep `limits.auto.tfvars.json`, Terraform
state, and OCI credentials private; they are ignored by Git.

## Validate and deploy

Run the read-only preflight first:

```bash
python -m limit_checker preflight --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

Deploy the complete stack with one command:

```bash
python scripts/deploy_stack.py apply --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

The script performs the required internal steps: Terraform creates the
Functions application, logging and archive access; OCI CLI packages and
deploys the code-only Function; Terraform then creates IAM, the schedule,
Notifications topic and subscription, and one Monitoring alarm per monitor.

Confirm each email subscription message sent by OCI. Alerts cannot be
delivered until confirmation.

## Verify

After the first scheduled run, open the Function invocation log in OCI Console
under **Observability & Management > Logging** in the configured region. Each
monitor should report `OK` or `WARNING`. `WARNING` means that the check ran
successfully and crossed its configured soft threshold. `ERROR` means the
monitor could not be checked.

The stack creates a Functions application, log group and invocation log, two
Dynamic Groups, three IAM policies, a Resource Scheduler schedule, a
Notifications topic and email subscriptions, and one Monitoring alarm per
monitor. It also creates a private archive bucket only when
`archive_bucket_name` is `null`.

The included template defines ten monitors: Compute Standard3, Standard E4,
Standard E5 and custom images; Block Volume count, total storage and backups;
Object Storage bucket count; Load Balancer flexible count; and tenancy IAM
policy count.

## Update or remove

After changing code or configuration, rerun preflight and the same `apply`
command. The deployment script updates the Function and Terraform reconciles
the managed resources.

To remove the stack:

```bash
python scripts/deploy_stack.py destroy --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

The script deletes the Function before its application. A supplied archive
bucket is preserved. Keep the Terraform state until cleanup is complete.
