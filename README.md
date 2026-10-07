# OCI limit warnings

## 1. Prerequisites

- Python 3.10+
- Terraform 1.3+
- OCI CLI 3.94+ configured with the target OCI profile
- An existing subnet with outbound access to OCI APIs
- OCI permissions to create Functions, Logging, Resource Scheduler,
  Monitoring alarms, Notifications, Dynamic Groups and IAM policies

Install the Python dependency:

```bash
python -m pip install -r requirements.txt
```

## 2. Create the customer configuration

Copy the example file. Edit only the copied file.

```bash
cp terraform/limits.example.tfvars.json terraform/limits.auto.tfvars.json
```

Windows PowerShell:

```powershell
Copy-Item terraform/limits.example.tfvars.json terraform/limits.auto.tfvars.json
```

Open `terraform/limits.auto.tfvars.json` and replace every value marked
`CHANGE HERE`:

- `region`
- `home_region`
- `tenancy_id`
- `function_compartment_id`
- `subnet_id`
- `schedule_start_utc`: future UTC timestamp, for example
  `2026-12-31T12:00:00Z`
- `email_recipients`
- `availability_domain` for every AD-scoped monitor

Optional values:

- `archive_bucket_name`: `null` creates a private bucket. Set an existing
  private bucket name to reuse it; the supplied bucket is preserved on destroy.
- `check_schedule_utc`: five-field UTC cron expression. `15 * * * *` runs once
  per hour at minute 15. OCI Resource Scheduler has a minimum one-hour
  interval.
- `warning_percent`: email threshold for each monitor. Default: `80`.

Keep `terraform/limits.auto.tfvars.json`, Terraform state and OCI credentials
private. They are ignored by Git.

## 3. Validate the selected limits

```bash
python -m limit_checker preflight --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

Fix any `ERROR` result before deployment.

## 4. Deploy

```bash
python scripts/deploy_stack.py apply --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

This command creates the Functions application, Function, log group and
invocation log, archive policy, two Dynamic Groups, three IAM policies,
Resource Scheduler schedule, Notifications topic and subscription, and one
Monitoring alarm per monitor.

## 5. Confirm email delivery

OCI sends a confirmation email to every address in `email_recipients`.
Click **Confirm subscription** in each email. No warning email can arrive
before confirmation.

## 6. Verify

After the first scheduled run, open OCI Console:

`Observability & Management > Logging > <invocation log>`

Each monitor must show `OK` or `WARNING`. `WARNING` means that usage reached
the configured threshold and its Monitoring alarm can send email. `ERROR`
means the monitor could not be checked.

## Monitored limits in the example

| Monitor | OCI limit | Scope |
| --- | --- | --- |
| `compute_standard3_cores` | Compute `standard3-core-count` | Availability domain |
| `compute_standard_e4_cores` | Compute `standard-e4-core-count` | Availability domain |
| `compute_standard_e5_cores` | Compute `standard-e5-core-count` | Availability domain |
| `compute_custom_images` | Compute `custom-image-count` | Region |
| `block_volume_count` | Block Storage `volume-count` | Availability domain |
| `block_total_storage_gb` | Block Storage `total-storage-gb` | Availability domain |
| `block_backup_count` | Block Storage `backup-count` | Region |
| `object_bucket_count` | Object Storage `bucket-count` | Region |
| `load_balancer_flexible_count` | Load Balancer `lb-flexible-count` | Region |
| `iam_policies_tenancy` | Identity `policies-count` | Tenancy |

## Update

After changing code or `limits.auto.tfvars.json`, run:

```bash
python -m limit_checker preflight --config terraform/limits.auto.tfvars.json --profile DEFAULT
python scripts/deploy_stack.py apply --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

## Destroy

```bash
python scripts/deploy_stack.py destroy --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

The Function is deleted before the Functions application. A supplied archive
bucket is preserved.
