# OCI limit warnings

## 1. Install prerequisites on the deployment machine

Install these tools using the package manager or installer for the operating
system:

- Git
- Python 3.10 or later, including `pip` and `venv`
- Terraform 1.3 or later
- OCI CLI 3.94 or later
- An OCI CLI profile for an OCI user allowed to create Functions, Logging,
  Resource Scheduler, Monitoring alarms, Notifications, Dynamic Groups and IAM
  policies

Verify the tools:

```bash
git --version
python3 --version
oci --version
terraform version
```

The Python version must be 3.10 or later. On systems where `python3` is
older, verify the versioned executable that will be used in section 3.

The deployment machine needs outbound HTTPS access to GitHub, PyPI, HashiCorp
and OCI APIs. The Function subnet configured later also needs outbound access
to OCI APIs.

## 2. Clone the repository

```bash
git clone https://github.com/adinan-tech/Freewheel-limits.git
cd Freewheel-limits
```

If the repository is already present, do not clone it again:

```bash
cd ~/Freewheel-limits
git pull
```

For a private repository, use a GitHub Personal Access Token as the password
when Git prompts for it.

## 3. Install the project Python dependency

Choose the installed Python 3.10+ executable and verify its version before
creating the virtual environment. On Oracle Linux 9, use `python3.11` because
the default `python3` command can still refer to Python 3.9.

Linux or macOS:

```bash
PYTHON_BIN=python3.11
$PYTHON_BIN --version
$PYTHON_BIN -m venv .venv
source .venv/bin/activate
python --version
python -m pip install -r requirements.txt
```

Replace `python3.11` with the command for the installed Python 3.10+ version
on another operating system.

Keep this virtual environment active while running the remaining commands.

## 4. Configure OCI CLI

Run:

```bash
oci setup config
```

Use the target tenancy, region and an OCI user that has permission to create
Functions, Logging, Resource Scheduler, Monitoring alarms, Notifications,
Dynamic Groups and IAM policies. Upload the generated public API key to that
OCI user, then verify the `DEFAULT` profile:

```bash
oci iam availability-domain list --profile DEFAULT
```

## 5. Create the customer configuration

Copy the example file. Edit only the copied file.

```bash
cp terraform/limits.example.tfvars.json terraform/limits.auto.tfvars.json
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

## 6. Validate the selected limits

```bash
python -m limit_checker preflight --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

Fix any `ERROR` result before deployment.

## 7. Deploy

```bash
python scripts/deploy_stack.py apply --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

This command creates the Functions application, Function, log group and
invocation log, archive policy, two Dynamic Groups, three IAM policies,
Resource Scheduler schedule, Notifications topic and subscription, and one
Monitoring alarm per monitor.

On a new stack, the script waits for the archive-read IAM policy to propagate
before creating the Function. This can take up to 90 seconds.

## 8. Confirm email delivery

OCI sends a confirmation email to every address in `email_recipients`.
Click **Confirm subscription** in each email. No warning email can arrive
before confirmation.

## 9. Verify

After the first scheduled run, open OCI Console:

`Observability & Management > Logging > <invocation log>`

Each monitor must show `OK` or `WARNING`. `WARNING` means that usage reached
the configured threshold and its Monitoring alarm can send email. `ERROR`
means the monitor could not be checked.

Also verify that the Function is `ACTIVE`, the Resource Scheduler schedule is
`ACTIVE`, and each email subscription is `ACTIVE` after its confirmation.

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
