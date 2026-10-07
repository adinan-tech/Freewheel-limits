# Limit checker (A2)

Copy `terraform/limits.example.tfvars.json` to `terraform/limits.auto.tfvars.json` and fill in the OCI region, tenancy OCID, recipient, subnet, and limits to monitor. The file is ignored by Git. A monitor name is a stable identifier for later metrics and alarms. `warning_percent` is the user's soft warning level; the hard value is read from OCI each run. Leave `availability_domain` as `null` unless the selected limit is AD-scoped.

Use Python 3.10 or newer on Windows, macOS, or Linux. Install `requirements.txt`, then run from the repository root:

```text
python -m limit_checker preflight --config terraform/limits.auto.tfvars.json
python -m limit_checker check --config terraform/limits.auto.tfvars.json
```

Both commands are read-only. `preflight` checks the configured limit names, scopes, support, and current data before deployment. `check` returns one JSON result per monitor: `OK`, `WARNING`, or `ERROR`. Exit code 1 means a monitor could not be checked; a warning alone exits 0. The OCI SDK finds its default config file for the current OS; use `--oci-config` and `--profile` to override it, or `--auth resource-principal` in OCI. A2 does not send metrics or email; A4 will consume the structured results.

OCI calls use the tenancy root OCID, so verify in A3 that each usage result matches the intended service-limit scope. A lower compartment quota can block creation before the tenancy hard limit is reached and needs a separate warning design. The global IAM policy monitor uses `service_name: "identity"`, `limit_name: "policies-count"`, and `availability_domain: null`. OCI does not expose policy usage through the service-limits availability API, so the checker counts policy objects in the tenancy and every active compartment.
