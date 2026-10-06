# Proposed limit-warning flow

This editable [draw.io diagram](limits-alert-flow.drawio) shows the Part A design. Phase A1 of [PROJECT_PLAN.md](PROJECT_PLAN.md) defines customer inputs in [the example configuration](terraform/limits.example.tfvars.json): which limits to watch, soft warning percentages, region, schedule, and recipients. The Function will read current hard limit values and usage directly from OCI. A2 will implement validation; A3 will test it in a tenancy.

The warning threshold triggers an email; it does not change the OCI hard limit. A selected limit that lacks usable Service Limits data needs a validated alternative before it can be monitored. IAM policy counts are planned for phase A5 using a separate counting method if needed.

Cloud Guard findings are Part B in phases B1 and B2. Their flow will be documented after their scope is agreed.
