# A3: OCI Function deployment

This stack follows the [Thunder framework](https://github.com/oracle-quickstart/oci-adoption-framework-thunder) pattern: small Terraform modules use named parameter maps and `for_each`. The modules create a Functions application and Function, an invocation log, a scheduled invocation, and two narrowly scoped identities: the schedule may invoke the Function, and the Function may read service limits. Existing customer subnets are reused.

## Before applying

1. Use an OCI identity that can create Functions, Resource Scheduler schedules, logs, dynamic groups, and policies. The identity's OCI SDK/provider config stays outside this repository.
2. Choose an existing subnet in the deployment region with access to the OCI APIs. Supply its OCID; this stack does not create a VCN.
3. Build and push the Function image to OCIR in the same region. From the repository root, use a versioned image name matching `function_image`:

   ```text
   docker build --platform linux/amd64 -f function/Dockerfile -t <region-key>.ocir.io/<namespace>/limit-checker:1.0.0 .
   docker push <region-key>.ocir.io/<namespace>/limit-checker:1.0.0
   ```

   The image uses Oracle's Python 3.12 Functions base images. Terraform consumes the pushed image; it does not build it.
4. Copy `limits.example.tfvars.json` to `limits.auto.tfvars.json` and fill every placeholder. Set `schedule_start_utc` far enough in the future for Terraform apply and IAM propagation. One stack runs in one OCI region; deploy another stack for another region.
5. Run the local read-only preflight from the repository root: `python -m limit_checker preflight --config terraform/limits.auto.tfvars.json`.

Then run `terraform -chdir=terraform init`, `terraform -chdir=terraform plan`, and `terraform -chdir=terraform apply`. Keep Terraform state in an approved backend; state and customer variable files are ignored by Git.

## Verify A3

Check Terraform's `function_id`, `schedule_id`, and `invocation_log_id` outputs. After the first scheduled run, inspect the invocation log for one `OK` or `WARNING` result per configured monitor. A monitor `ERROR` means the Function invocation fails so the issue is visible in logs. Confirm the usage is for the intended tenancy, region, and availability domain. If that live result does not match the service-limit scope, adjust the checker before adding email alarms.

OCI Function configuration has a small size limit; this stack checks for a roughly 3.5 KB ceiling. A larger monitor set will need an external configuration store in a later phase. The schedule uses UTC and has a one-hour minimum interval.

Reference: [OCI Functions Terraform resource](https://registry.terraform.io/providers/oracle/oci/latest/docs/resources/functions_function), [Resource Scheduler for Functions](https://docs.oracle.com/en-us/iaas/Content/Functions/Tasks/functionsschedulingfunctions-about.htm), [Function logging source](https://docs.oracle.com/en-us/iaas/Content/Logging/Task/functions_eg.htm), and [OCI Functions base image change](https://docs.oracle.com/en-us/iaas/Content/servicechanges.htm).
