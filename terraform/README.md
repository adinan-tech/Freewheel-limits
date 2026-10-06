# A3: deploy the limit checker

This stack uses Thunder-style Terraform modules for the OCI Functions application, invocation log, Resource Scheduler schedule, archive bucket, and least-privilege IAM. The checker itself is a **code-only Python Function** deployed as a ZIP. It needs no Docker image or OCIR repository. The current OCI Terraform provider does not create code-only Functions, so deployment has two Terraform applies with an OCI CLI step between them.

## Prerequisites

- An OC1 region that supports code-only Functions, an existing subnet with OCI API access, and permissions to create Functions, schedules, logs, an Object Storage bucket, dynamic groups, and policies.
- Terraform, Python with pip, and OCI CLI **3.94 or newer**, configured for the target tenancy. Credentials stay outside this repository.
- An approved Terraform state backend for customer use. This stack does not create a VCN.

## Deploy

From the repository root:

1. Copy `terraform/limits.example.tfvars.json` to `terraform/limits.auto.tfvars.json`. Replace all placeholders. Set `schedule_start_utc` far enough ahead for deployment and IAM propagation. One stack covers one region.
2. Run `python -m limit_checker preflight --config terraform/limits.auto.tfvars.json` to validate selected limits against OCI.
3. Run `terraform -chdir=terraform init` and `terraform -chdir=terraform apply`. The first apply creates the application, invocation log, private archive bucket, and narrowly scoped archive-read policy.
4. Run `python scripts/deploy_zip.py --config terraform/limits.auto.tfvars.json`. Add `--profile NAME` if needed. The script packages Linux x86 Python dependencies, uploads a versioned ZIP to the bucket, creates or updates the code-only Function, and writes its OCID to the ignored `terraform/function.auto.tfvars.json` file. Rerunning updates the same Function.
5. Run `terraform -chdir=terraform apply` again. This creates the reader IAM and scheduled invocation for that Function.

On later code or configuration changes, rerun steps 2, 4, and 5. Allow for IAM propagation before the first scheduled run. Keep both auto-tfvars files and Terraform state private and out of Git.

## Verify A3

Check the `function_id`, `schedule_id`, and `invocation_log_id` Terraform outputs. After the first scheduled run, inspect invocation logs for one `OK` or `WARNING` result per monitor and confirm tenancy, region, and availability-domain scope. A monitor `ERROR` causes the invocation to fail visibly in logs. Do not mark A3 complete until a live scheduled run succeeds.

The OCI Python SDK makes the archive too large for 25 MB direct upload, so the script uses Object Storage's 250 MB archive limit. Function configuration is limited to 4 KB; a larger monitor set will need external configuration in a later phase. The schedule uses UTC and has a one-hour minimum interval.

References: [Python ZIP layout](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functions-codeonly-python.htm), [creating code-only Functions](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functions-codeonly-creating.htm), [supported runtimes](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/languagessupportedbyfunctions.htm), [Resource Scheduler](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functionsschedulingfunctions-about.htm).
