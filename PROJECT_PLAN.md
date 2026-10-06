# OCI proactive alerts project plan

## Goal and order

Build two independent alerting workstreams:

1. **Part A — Limit warnings (first):** Email when selected OCI resource usage crosses a configurable warning threshold below the hard limit. The warning threshold does not change the OCI limit.
2. **Part B — Cloud Guard findings (later):** Email selected security findings detected by Cloud Guard. This workstream does not depend on the limit checker.

The workstreams may share an OCI Notifications topic and recipients. Keep them separate from the existing limit increase and region-copy project; reuse discovery code only if useful.

See the editable [Part A draw.io flow](limits-alert-flow.drawio) and its [notes](ARCHITECTURE.md). Confirm the design during phase A1.

Mark a phase complete only after its completion criteria are verified. Record the evidence and date in the progress log. Do not mark a phase complete merely because code was written.

## Part A — Limit warnings

### [x] A1. Define reusable configuration and data checks

- The customer supplies monitors in [terraform/limits.example.tfvars.json](terraform/limits.example.tfvars.json): service and limit names to watch, optional availability domain, and a **soft warning percentage**. The file also holds the tenancy, region, optional subscription, UTC schedule, and email recipients. It contains no hard limit values. Copy it to `terraform/limits.auto.tfvars.json` for a deployment; A2-A4 will consume it.
- During preflight, discover limit definitions and check each configured name, scope, and `is_resource_availability_supported` flag. Reject unsupported entries clearly. At each check, read the tenancy's current **hard service limit** with `ListLimitValues` and current usage with `GetResourceAvailability`; verify that the returned usage matches the limit's tenancy/region/AD scope. Calculate `used / hard_limit` only when both values are valid and the hard limit is positive. A lower compartment quota can block resources earlier; that needs a separate effective-quota warning if compartment monitoring is later added.
- Use Function -> custom metric -> Monitoring alarm -> Notifications email. One alarm is created per configured monitor; warning percentages are configurable. The warning never changes an OCI limit.
- The Function needs inspect access for limit definitions/values and read access to resource availability. Actual permissions and API behavior will be checked during A3 in the deployment tenancy.

**Done:** The configuration contract, API checks, and alert path are specified without customer-specific hard limits. OCI documents the [definition scope and support flag](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/limits/models/oci.limits.models.LimitDefinitionSummary.html), [hard limit values and availability APIs](https://docs.oracle.com/en-us/iaas/tools/python/latest/api/limits/client/oci.limits.LimitsClient.html), and [required IAM permissions](https://docs.oracle.com/en-us/iaas/Content/General/service-limits/overview.htm).

### [x] A2. Build the Python limit checker

- Implement configurable limit selection, live OCI hard-limit and usage calls, scope-aware usage calculations, and structured results.
- Keep OCI access and result publishing separate so the calculation can be tested locally.
- Add a preflight command that validates the customer's configured names/scopes and tests API availability before deployment. Test normal values, zero or missing limits, unsupported limits, and API errors with representative responses.

**Done:** The local `preflight` and `check` commands return structured results for configured monitors. Eight local tests pass with representative OCI definition, value, and availability fields, including AD and regional scopes, changed hard limits, threshold boundary, missing values, unsupported limits, and API errors. Live OCI behavior remains for A3.

### [ ] A3. Deploy OCI infrastructure and code-only Function

- Package the checker as a ZIP and deploy it as a code-only Python Function with OCI CLI. Use Terraform to create the OCI Functions application, configure networking and logging, and reuse customer subnets where appropriate.
- Use Terraform to create the Resource Scheduler schedule and least-privilege IAM dynamic groups and policies needed to invoke the Function and read limits.
- Run the scheduled Function in the pilot tenancy and inspect its logs and results.

**Done when:** A scheduled live invocation reads the selected pilot limits successfully; no email alert is required yet.

**Current status:** The ZIP packaging/deployment script and Terraform modules for the Functions application, private archive bucket, invocation logging, reader IAM, and Resource Scheduler are written. Deployment is pending a customer-selected tenancy/region/subnet, OCI CLI 3.94+, provider validation, and a live scheduled invocation. A3 is not complete.

### [ ] A4. Add warning emails

- Implement the alert path chosen in A1. The current proposal is Function to custom metrics to Monitoring alarms to Notifications email.
- Use Terraform to create the Monitoring alarms, Notifications topic, and email subscriptions for that path. Recipients can include individual addresses or a distribution-list alias; the recipient or list owner must confirm each subscription.
- Generate an alarm per configured monitor and include its identity, scope, region, and usage in the alert where supported.
- Verify alert and recovery behavior without repeated unwanted emails.

**Done when:** A live threshold test sends the expected email and a below-threshold check does not send a warning.

### [ ] A5. Extend limit coverage

- Add the agreed IAM policy count or statement limit using a validated counting method.
- Add more compute and storage limits, regions, and compartments through configuration without changing checker code.
- Recheck scope and usage calculations for every newly added limit.

**Done when:** Each agreed limit is covered by a verified calculation and alert test, or is recorded as unsupported with a reason.

### [ ] A6. Harden and hand over Part A

- Alert on failed or missed checks, document deployment, configuration, and recovery, and verify repeatable Terraform deployment.
- Test threshold changes, subscription confirmation, and the agreed check interval.
- Review results and alert behavior with the customer.

**Done when:** Health checks work, operating instructions are complete, and the customer accepts Part A.

## Part B — Cloud Guard findings (after Part A)

### [ ] B1. Define Cloud Guard alert scope

- Confirm that Cloud Guard is enabled, its reporting region and targets, which findings or risk levels matter, and the email recipients.
- Decide whether to reuse the limit-warning Notifications topic or use a separate topic.

**Done when:** The customer agrees on the findings to email and the OCI configuration required.

### [ ] B2. Configure and test Cloud Guard email

- Configure the Cloud Event responder, Events rule, and Notifications email subscription in the Cloud Guard reporting region.
- Test with a new finding and verify that selected findings arrive while excluded findings do not.

**Done when:** The email test and filtering test pass, and operating instructions are documented.

## Open decisions

### Part A — Limit warnings

- Which IAM policy ceiling matters: policy objects, statements per policy, or statements per compartment hierarchy.
- Each deployment supplies its own monitored limits, scopes, thresholds, regions, compartments, and recipients. These are inputs, not project design decisions.
- Access to a deployment tenancy is needed to test configured limits and IAM permissions in A3.

### Part B — Cloud Guard (decide later)

- Reporting region, targets, finding filters, and recipients.

## Progress log

- 2026-10-06: Plan reordered into limit warnings first and Cloud Guard findings later; no phase completed yet.
- 2026-10-06: Named the workstreams Part A (limit warnings) and Part B (Cloud Guard findings).
- 2026-10-06: Split Part A into six development phases (A1-A6); Part B remains separate (B1-B2). No phase completed yet.
- 2026-10-06: Made Terraform resource deployment explicit in A3 and A4.
- 2026-10-06: Added an A3 Terraform module for Resource Scheduler and its invoke permissions. A3 remains open: Function packaging, networking, logging, runtime IAM, and a live scheduled run are still required.
- 2026-10-06: Drafted A1 pilot candidates and alert decisions from OCI documentation. A1 remains open pending customer choices and live availability checks.
- 2026-10-06: Completed A1 as a reusable configuration design. Customer-specific limits move to deployment inputs; live checks remain in A2/A3.
- 2026-10-06: Clarified A1: users select resources and soft warning percentages; the checker reads current hard limit values directly from OCI.
- 2026-10-06: Completed A2 local checker, OCI adapter, configuration validation, and eight passing tests. A live tenancy check remains in A3.
- 2026-10-06: Audited A2 for platform independence. Paths use `pathlib` and the OCI SDK's OS-specific default config lookup; no platform-specific shell or filesystem code is required.
- 2026-10-06: Built the A3 Function package and Terraform modules/root stack using the Thunder parameter-map pattern. Nine local Python tests pass and Terraform formatting passes; provider download and live OCI validation remain unavailable.
- 2026-10-06: Revised A3 to use a code-only Python ZIP and OCI CLI instead of an OCIR image. The OCI SDK exceeds the 25 MB direct-upload limit, so Terraform also creates a private Object Storage bucket for the ZIP. Terraform provisions the surrounding resources in two applies. Live scheduled verification remains pending.
