# Frankfurt A3 pilot: manual walkthrough

Run these steps in PowerShell from the repository root. The stack creates a
code-only Function, hourly schedule, invocation logging, and email alarms. The
values below were checked read-only on 2026-10-07. They are pilot choices, not
a customer-approved list.

| Input | Pilot value |
| --- | --- |
| OCI profile | `DEFAULT` in `%USERPROFILE%\.oci\config` |
| Function region | `eu-frankfurt-1` |
| Home region for IAM | `us-ashburn-1` |
| Tenancy | `ocid1.tenancy.oc1..aaaaaaaaz3zvzfb4afndqhyljo75yoat5azx6yw5hppwxqv3felvg3flex4q` |
| Compartment | `ocid1.compartment.oc1..aaaaaaaa7pi4cxii45qocqppd7pomh4qcefj7biaygc2jqz7wdgqitrwwwia` (`anicolescu`) |
| Subnet | `ocid1.subnet.oc1.eu-frankfurt-1.aaaaaaaa6shpw2yfihcrs5uuq7dytdz7xgpwbr3nah6gslznxlocnqsd2hdq` (`private` in `Data locality - ZLxm`) |

The subnet is private and available, with an active NAT gateway and outbound
route. The deploying identity needs rights to manage Functions, Resource
Scheduler, Logging, Object Storage, dynamic groups, and policies. Keep OCI
credentials outside this repository.

## 1. Check tools and access

```powershell
oci --version
terraform version
python --version
python -m pip install -r requirements.txt
oci iam compartment get --profile DEFAULT --region eu-frankfurt-1 --compartment-id ocid1.compartment.oc1..aaaaaaaa7pi4cxii45qocqppd7pomh4qcefj7biaygc2jqz7wdgqitrwwwia --query data.name --raw-output
```

Expect OCI CLI 3.94+, Terraform 1.3+, Python 3.10+, and `anicolescu` from the
last command. Resolve credentials or IAM access before continuing if it fails.

## 2. Fill the ignored pilot configuration

```powershell
Copy-Item terraform/limits.example.tfvars.json terraform/limits.auto.tfvars.json
notepad terraform/limits.auto.tfvars.json
```

Replace the file content with the JSON below. Replace
`REPLACE_WITH_FUTURE_UTC_TIME` with a future RFC 3339 UTC time at least two
hours away to allow for deployment and IAM propagation. This prints a candidate:

```powershell
(Get-Date).ToUniversalTime().AddHours(2).ToString('yyyy-MM-ddTHH:mm:ssZ')
```

Replace `REPLACE_WITH_EMAIL` with an address you control. A3 does not send
email, but the current configuration contract requires one. The 80% thresholds
are pilot defaults and do not change OCI hard limits.

```json
{
  "region": "eu-frankfurt-1",
  "home_region": "us-ashburn-1",
  "tenancy_id": "ocid1.tenancy.oc1..aaaaaaaaz3zvzfb4afndqhyljo75yoat5azx6yw5hppwxqv3felvg3flex4q",
  "function_compartment_id": "ocid1.compartment.oc1..aaaaaaaa7pi4cxii45qocqppd7pomh4qcefj7biaygc2jqz7wdgqitrwwwia",
  "archive_bucket_name": null,
  "subnet_id": "ocid1.subnet.oc1.eu-frankfurt-1.aaaaaaaa6shpw2yfihcrs5uuq7dytdz7xgpwbr3nah6gslznxlocnqsd2hdq",
  "schedule_start_utc": "REPLACE_WITH_FUTURE_UTC_TIME",
  "check_schedule_utc": "0 * * * *",
  "email_recipients": ["REPLACE_WITH_EMAIL"],
  "monitors": {
    "compute_standard3_cores": {
      "service_name": "compute",
      "limit_name": "standard3-core-count",
      "availability_domain": "RiYU:EU-FRANKFURT-1-AD-1",
      "warning_percent": 80
    },
    "block_volume_count": {
      "service_name": "block-storage",
      "limit_name": "volume-count",
      "availability_domain": "RiYU:EU-FRANKFURT-1-AD-1",
      "warning_percent": 80
    },
    "object_bucket_count": {
      "service_name": "object-storage",
      "limit_name": "bucket-count",
      "availability_domain": null,
      "warning_percent": 80
    }
  }
}
```

`terraform/limits.auto.tfvars.json` is the only customer configuration file
and is Git-ignored. Do not commit it, Terraform state, or OCI credentials.

For this pilot, `archive_bucket_name: null` creates a dedicated private bucket.
To reuse a bucket **before the first apply**, set this field to its name. It
must be in the same tenancy and Frankfurt region, have `NoPublicAccess`, and
allow the deploying user to upload objects. Terraform reads its compartment
and creates a Function read policy scoped to the selected bucket and the single
ZIP object `limit_warnings_checker.zip`; it does not manage or delete the
supplied bucket. Functions applications in `anicolescu` can read only that ZIP.
Keep the choice stable after deployment.

## 3. Run read-only preflight and check

```powershell
python -m limit_checker preflight --config terraform/limits.auto.tfvars.json --profile DEFAULT
python -m limit_checker check --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

Expect one result per configured monitor without `ERROR`, with the intended
region, scope, hard limit, and usage. Stop if a limit is unsupported or its
scope is wrong.

## 4. Choose Terraform state storage

Choose an approved state backend before `terraform init` or apply. Terraform
defaults to local `terraform/terraform.tfstate`; use that only for a controlled
pilot if local state is acceptable. Keep a private backup. A customer
deployment needs its approved shared backend. Do not start a second state for
the same resources; migrate state if changing backends later.

## 5. Deploy the full stack

```powershell
python scripts/deploy_stack.py apply --config terraform/limits.auto.tfvars.json --profile DEFAULT
```

This one command performs the required internal stages: it creates the
application, logging and bucket resources; packages and uploads the ZIP;
creates or updates the Function; then passes the Function OCID to Terraform
internally to create IAM, schedule, topic, subscription, and alarms. It does
not create another customer configuration file.

## 6. Verify the scheduled run

After the first hourly run, open the invocation log identified above in OCI
Console **Observability & Management > Logging** in Frankfurt. Search from the
schedule start time. Verify every configured monitor has `OK` or `WARNING`,
with the selected scope, valid hard limit, and usage. A `WARNING` is a
successful check above the pilot soft threshold; it can also trigger its email
alarm. A missing run,
`ERROR`, or failed invocation means A3 is not complete.

Record the schedule ID, log ID, run time, and results in `PROJECT_PLAN.md`,
then mark A3 done. A local `check` command is not scheduled-run evidence.

## Recovery

- Preflight error: correct the monitor, scope, profile, or IAM access and rerun
  step 3. Do not deploy an unsupported limit.
- Terraform error: keep the same state, fix the cause, rerun `plan` and `apply`.
- ZIP deployment error: fix the CLI, permission, or packaging issue and rerun
  step 5; the script finds an existing Function by name.
- Missing or failing schedule: inspect the schedule, invocation log, subnet
  egress, and IAM policies. Allow for IAM propagation. A manual invocation may
  diagnose the Function, but only a scheduled success completes A3.

The CLI-created Function is not owned by Terraform. During later cleanup,
delete it separately before removing the Terraform-managed application. A
Terraform-managed archive bucket must be emptied before removal; a supplied
bucket remains in place, including its uploaded ZIP objects. Retain Terraform
state until cleanup is complete.
