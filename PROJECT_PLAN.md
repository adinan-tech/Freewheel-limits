# OCI proactive limit and Cloud Guard alerts

## Goal

Alert before selected OCI limits block work, and email selected Cloud Guard findings. Start with compute, storage, and IAM policy limits. Keep this alerting project separate from the existing limit increase and region-copy workflow; reuse its discovery code only if useful.

Mark a phase complete only after its completion criteria are verified. Record the result in this file. Do not mark a phase complete merely because code was written.

## Phases

### [ ] 1. Scope and feasibility

- Confirm the exact compute, storage, and IAM policy limits, their scopes (tenancy, region, availability domain, or compartment), and the first regions and compartments to cover.
- Check which selected limits expose used and available values through OCI Service Limits, and define a separate counting method where they do not.
- Confirm the threshold, check frequency, email recipients, OCI access, and Cloud Guard reporting region and finding filters.

**Done when:** A support matrix and agreed MVP configuration are recorded here, including unsupported limits and required access.

### [ ] 2. Limit-alert MVP

- Build a configurable, scheduled OCI check for the supported initial compute and storage limits.
- Calculate usage against each limit's effective scope; send threshold emails through OCI Notifications.
- Prevent repeat emails while a limit remains above the threshold, and report check failures.

**Done when:** Tests cover threshold crossing, recovery, unsupported limits, and failed API calls; a live test delivers an email for a selected limit.

### [ ] 3. Cloud Guard email alerts

- Configure the Cloud Event responder, Events rule, and Notifications email subscription in the Cloud Guard reporting region.
- Filter findings according to the agreed scope and risk levels.

**Done when:** A new test finding produces the expected email and unwanted findings are filtered out.

### [ ] 4. IAM policy limits and rollout

- Add monitoring for the agreed IAM policy count or statement limits using the validated method from phase 1.
- Add more limits and regions, deployment automation, operating instructions, and failure monitoring.

**Done when:** The agreed policy limit and expanded cases are tested, deployment can be repeated, and the customer accepts the alert behavior.

## Open decisions

- Exact first compute and storage limit names and scopes.
- Which IAM policy ceiling matters: policy objects, statements per policy, or statements per compartment hierarchy.
- Thresholds, cadence, recipients, regions, compartments, and Cloud Guard finding filters.
- Customer tenancy access and who will perform live validation.

## Progress log

- 2026-10-06: Plan created; no phase completed yet.
