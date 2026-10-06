# OCI proactive alerts project plan

## Goal and order

Build two independent alerting workstreams:

1. **Limit warnings first:** Email when selected OCI resource usage crosses a configurable warning threshold below the hard limit. The warning threshold does not change the OCI limit.
2. **Cloud Guard later:** Email selected security findings detected by Cloud Guard. This workstream does not depend on the limit checker.

The workstreams may share an OCI Notifications topic and recipients. Keep them separate from the existing limit increase and region-copy project; reuse discovery code only if useful.

See the editable [draw.io limit-warning flow](limits-alert-flow.drawio) and its [notes](ARCHITECTURE.md). Confirm the design during phase 1.

Mark a phase complete only after its completion criteria are verified. Record the evidence and date in the progress log. Do not mark a phase complete merely because code was written.

## Limit warnings

### [ ] 1. Define and validate initial limits

- Confirm the exact first compute and storage limits, their scopes (tenancy, region, availability domain, or compartment), and the regions and compartments to monitor.
- Verify how to obtain used and available values for each limit; record unsupported limits and alternatives.
- Agree on configurable thresholds, check frequency, email recipients, and OCI read access.
- Decide whether the MVP sends directly through Notifications or publishes custom metrics for Monitoring alarms. The current architecture draft uses custom metrics and alarms.

**Done when:** A support matrix, alert design choice, and agreed MVP configuration are recorded here.

### [ ] 2. Build and test the limit-warning MVP

- Implement a scheduled Python OCI Function that checks the selected limits and calculates usage against the correct scope.
- Send threshold emails through the chosen OCI alert path; include the limit identity, scope, usage, threshold, and region in alerts where supported.
- Test threshold crossing, recovery, missing usage data, API failures, and a failed or missed check.

**Done when:** Tests pass and a live check for at least one selected limit delivers the expected email without repeated unwanted alerts.

### [ ] 3. Extend and operate limit warnings

- Add the agreed IAM policy count or statement limit using a validated counting method.
- Add approved limits, regions, and compartments; automate deployment and document configuration and recovery.
- Monitor checker failures and verify that alert thresholds can be changed safely.

**Done when:** The agreed policy limit and expanded cases are tested, deployment is repeatable, and the customer accepts the limit-warning behavior.

## Cloud Guard findings (after limit warnings)

### [ ] 4. Define Cloud Guard alert scope

- Confirm that Cloud Guard is enabled, its reporting region and targets, which findings or risk levels matter, and the email recipients.
- Decide whether to reuse the limit-warning Notifications topic or use a separate topic.

**Done when:** The customer agrees on the findings to email and the OCI configuration required.

### [ ] 5. Configure and test Cloud Guard email

- Configure the Cloud Event responder, Events rule, and Notifications email subscription in the Cloud Guard reporting region.
- Test with a new finding and verify that selected findings arrive while excluded findings do not.

**Done when:** The email test and filtering test pass, and operating instructions are documented.

## Open decisions

### Limit warnings

- Exact first compute and storage limit names and scopes.
- Which IAM policy ceiling matters: policy objects, statements per policy, or statements per compartment hierarchy.
- Thresholds, check frequency, recipients, regions, compartments, and customer tenancy access.
- Direct Notifications or custom metrics plus Monitoring alarms for the MVP.

### Cloud Guard (decide later)

- Reporting region, targets, finding filters, and recipients.

## Progress log

- 2026-10-06: Plan reordered into limit warnings first and Cloud Guard findings later; no phase completed yet.
